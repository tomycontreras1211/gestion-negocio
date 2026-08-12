import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_qrcode_scanner import qrcode_scanner
import json

# --- CONFIGURACIÓN DE SEGURIDAD ---
PASSWORD_CORRECTA = "1211"  # Cámbiala por tu contraseña

def check_password():
    if "password_correcta" not in st.session_state:
        st.session_state.password_correcta = False
        
    if not st.session_state.password_correcta:
        st.text_input("Ingrese la clave para acceder:", type="password", key="password_input")
        if st.button("Acceder"):
            if st.session_state.password_input == PASSWORD_CORRECTA:
                st.session_state.password_correcta = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

# --- INICIO DE LA APP ---
if check_password():
    if not firebase_admin._apps:
        firebase_credentials = json.loads(st.secrets["FIREBASE_CONFIG"])
        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    st.title("🛒 Gestión Integral")

    if "carrito" not in st.session_state:
        st.session_state.carrito = []

    tab1, tab2, tab3 = st.tabs(["📦 Productos", "💰 Ventas / Caja", "📊 Historial / Reportes"])

    def obtener_categorias():
        cat_ref = db.collection("categorias").stream()
        lista = sorted([c.to_dict().get("nombre") for c in cat_ref])
        if not lista:
            lista = ["Bebidas", "Lácteos", "Almacén", "Limpieza", "Panadería"]
        return lista

    def obtener_categorias_con_id():
        cat_ref = db.collection("categorias").stream()
        lista = []
        for c in cat_ref:
            data = c.to_dict()
            lista.append({"id": c.id, "nombre": data.get("nombre")})
        return sorted(lista, key=lambda x: x["nombre"])

# --- TAB 1: GESTIÓN DE PRODUCTOS ---
    with tab1:
        st.header("📦 Gestión de Inventario")

        # --- SECCIÓN DE BÚSQUEDA Y FILTRO ---
        st.subheader("Buscar y Filtrar")
        
        # Integración del escáner
        usar_esc_inv = st.checkbox("📷 Escanear código para buscar producto", key="chk_esc_inv")
        cod_escaneado = ""
        if usar_esc_inv:
            cod_escaneado = qrcode_scanner(key="scanner_inv")
            if cod_escaneado:
                st.success(f"Código detectado: {cod_escaneado}")

        col_b1, col_b2 = st.columns([0.7, 0.3])
        
        # Si se escanea algo, se precarga en el input de búsqueda
        valor_busqueda = cod_escaneado if cod_escaneado else ""
        busq_prod = col_b1.text_input("🔍 Buscar por nombre o código", value=valor_busqueda, key="busq_inv")
        cat_prod = col_b2.selectbox("Filtrar categoría", ["Todas"] + obtener_categorias(), key="cat_inv")

        # --- OBTENCIÓN Y FILTRADO DE PRODUCTOS ---
        prods_ref = db.collection("productos").stream()
        productos_lista = [p for p in prods_ref]

        filtrados = []
        for p in productos_lista:
            d = p.to_dict()
            # Criterios de filtrado
            c_nom = not busq_prod or busq_prod.lower() in d.get('nombre', '').lower() or \
                    busq_prod.lower() in str(d.get('codigo', '')).lower()
            c_cat = cat_prod == "Todas" or d.get('categoria') == cat_prod
            
            if c_nom and c_cat:
                filtrados.append((p.id, d))

        # --- MOSTRAR PRODUCTOS ---
        if filtrados:
            st.write(f"Mostrando {len(filtrados)} productos:")
            for pid, item in filtrados:
                with st.expander(f"{item.get('nombre')} — Stock: {item.get('stock')} | Precio: ${item.get('precio', 0):.2f}"):
                    c_edit_col1, c_edit_col2 = st.columns(2)
                    
                    with c_edit_col1:
                        nuevo_nombre = st.text_input("Nombre", value=item.get('nombre'), key=f"nom_{pid}")
                        nuevo_precio = st.number_input("Precio", value=float(item.get('precio', 0)), key=f"pre_{pid}")
                    
                    with c_edit_col2:
                        nuevo_stock = st.number_input("Stock", value=float(item.get('stock', 0)), key=f"stk_{pid}")
                        nuevo_cod = st.text_input("Código", value=item.get('codigo', ''), key=f"cod_{pid}")

                    if st.button("💾 Guardar Cambios", key=f"btn_save_{pid}"):
                        db.collection("productos").document(pid).update({
                            "nombre": nuevo_nombre,
                            "precio": nuevo_precio,
                            "stock": nuevo_stock,
                            "codigo": nuevo_cod
                        })
                        st.success("¡Producto actualizado!")
                        st.rerun()

                    if st.button("🗑️ Eliminar Producto", key=f"btn_del_{pid}"):
                        db.collection("productos").document(pid).delete()
                        st.rerun()
        else:
            st.warning("No se encontraron productos.")

        st.divider()
        # --- SECCIÓN PARA AGREGAR NUEVO PRODUCTO ---
        with st.expander("➕ Agregar nuevo producto"):
            n_nombre = st.text_input("Nombre del producto")
            n_precio = st.number_input("Precio base", min_value=0.0)
            n_stock = st.number_input("Stock inicial", min_value=0.0)
            n_cat = st.text_input("Categoría")
            n_cod = st.text_input("Código (opcional)")
            
            if st.button("Guardar nuevo producto"):
                if n_nombre:
                    db.collection("productos").add({
                        "nombre": n_nombre,
                        "precio": n_precio,
                        "stock": n_stock,
                        "categoria": n_cat,
                        "codigo": n_cod
                    })
                    st.success("Producto agregado correctamente")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio")
# --- TAB 2: VENTAS / CAJA (CARRITO) ---
    with tab2:
        st.header("🛒 Caja / Carrito de Ventas")

        prods_ref = db.collection("productos").stream()
        productos_dict = {p.id: p.to_dict() for p in prods_ref}

        if productos_dict:
            st.subheader("🧾 Ticket Actual")
            if st.session_state.carrito:
                total_general = 0
                for i, item_c in enumerate(st.session_state.carrito):
                    unidad_txt = "kg" if item_c['es_peso'] else "unid."
                    col_t1, col_t2 = st.columns([0.8, 0.2])
                    col_t1.write(f"• **{item_c['nombre']}** ({item_c['cantidad']:.3f} {unidad_txt}) — **${item_c['subtotal']:.2f}**")
                    if col_t2.button("❌", key=f"quitar_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()
                    total_general += item_c['subtotal']

                st.divider()
                st.markdown(f"### Total a Pagar: ${total_general:.2f}")

                col_c1, col_c2 = st.columns(2)
                if col_c1.button("✅ Confirmar Venta Total"):
                    from datetime import datetime
                    
                    lista_items_guardar = []
                    for item_c in st.session_state.carrito:
                        lista_items_guardar.append({
                            "nombre": item_c['nombre'],
                            "cantidad": item_c['cantidad'],
                            "subtotal": item_c['subtotal']
                        })
                        
                    db.collection("ventas").add({
                        "fecha": datetime.now(),
                        "total": total_general,
                        "items": lista_items_guardar
                    })
                    
                    for item_c in st.session_state.carrito:
                        p_ref = db.collection("productos").document(item_c['id'])
                        p_data = p_ref.get().to_dict()
                        if p_data:
                            nuevo_stock = float(p_data.get('stock', 0)) - item_c['cantidad']
                            p_ref.update({"stock": nuevo_stock})

                    st.success("¡Venta registrada con éxito y stock actualizado!")
                    st.session_state.carrito = []
                    st.rerun()

                if col_c2.button("🗑️ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
            else:
                st.info("El carrito está vacío. Agrega productos desde el catálogo de abajo.")

            st.divider()
            st.subheader("Catálogo de Productos")
            
            usar_esc = st.checkbox("📷 Usar escáner de cámara para venta rápida", key="chk_cam_venta")
            codigo_leido_esc = ""
            if usar_esc:
                codigo_leido_esc = qrcode_scanner(key="scanner_carrito")
                if codigo_leido_esc:
                    st.success(f"Código escaneado: {codigo_leido_esc}")

            col_f1, col_f2 = st.columns(2)
            busq_v = col_f1.text_input("🔍 Buscar producto", key="busq_cart")
            cat_v = col_f2.selectbox("Filtrar categoría", ["Todas"] + obtener_categorias(), key="cat_cart")

            filtrados = {}
            for pid, d in productos_dict.items():
                if codigo_leido_esc and str(codigo_leido_esc).strip() != str(d.get('codigo', '')).strip():
                    continue
                c_nom = not busq_v or busq_v.lower() in d['nombre'].lower() or busq_v.lower() in str(d.get('codigo', '')).lower()
                c_cat = cat_v == "Todas" or d.get('categoria') == cat_v
                if c_nom and c_cat:
                    filtrados[pid] = d

            if filtrados:
                st.write("Despliega cada producto para ver su imagen y opciones de carga:")
                
                for pid, item in filtrados.items():
                    col_min_img, col_min_exp = st.columns([0.15, 0.85])
                    
                    with col_min_img:
                        url_img = item.get('imagen', '')
                        if url_img:
                            try:
                                st.image(url_img, width=50)
                            except:
                                st.write("📦")
                        else:
                            st.write("📦")
                            
                    with col_min_exp:
                        titulo_acordeon = f"{item['nombre']} — ${float(item.get('precio', 0)):.2f} (Stock: {item.get('stock', 0)})"
                        
                        with st.expander(titulo_acordeon):
                            c_img, c_opc = st.columns([1, 1.5])
                            
                            with c_img:
                                if url_img:
                                    try:
                                        st.image(url_img, width=150, caption=item['nombre'])
                                    except:
                                        st.info("Sin imagen")
                                else:
                                    st.info("Sin imagen")

                            with c_opc:
                                st.write(f"**Categoría:** {item.get('categoria', 'General')}")
                                st.write(f"**Precio base / Kilo:** ${item.get('precio', 0):.2f}")
                                st.write(f"**Stock disponible:** {item.get('stock', 0)}")

                                es_peso = st.checkbox("⚖️ Es por peso / medida", key=f"chk_peso_{pid}")
                                precio_b = float(item.get('precio', 0))

                                cantidad_a_agregar = 1.0
                                subtotal = 0.0

                                if not es_peso:
                                    cantidad_a_agregar = st.number_input("Cantidad (Unid.)", min_value=1.0, step=1.0, value=1.0, key=f"cant_{pid}")
                                    subtotal = precio_b * cantidad_a_agregar
                                else:
                                    sub_op = st.radio("Cálculo:", ["Kilos / Gramos", "Dinero exacto ($)"], key=f"subop_{pid}")
                                    if sub_op == "Kilos / Gramos":
                                        cantidad_a_agregar = st.number_input("Kilos (Ej: 0.5)", min_value=0.01, value=0.5, step=0.1, format="%.3f", key=f"kg_{pid}")
                                        subtotal = precio_b * cantidad_a_agregar
                                        st.caption(f"Cobrar: **${subtotal:.2f}**")
                                    else:
                                        dinero_ing = st.number_input("Dinero ($)", min_value=1.0, value=500.0, step=50.0, key=f"din_{pid}")
                                        if precio_b > 0:
                                            cantidad_a_agregar = dinero_ing / precio_b
                                            subtotal = dinero_ing
                                            st.caption(f"Equivale a: **{cantidad_a_agregar * 1000:.0f} g** ({cantidad_a_agregar:.3f} kg)")
                                        else:
                                            cantidad_a_agregar = 0.0
                                            subtotal = 0.0

                                if st.button("➕ Agregar al Ticket", key=f"btn_add_{pid}"):
                                    stock_actual = float(item.get('stock', 0))
                                    en_carrito = sum([x['cantidad'] for x in st.session_state.carrito if x['id'] == pid])
                                    
                                    if stock_actual >= (en_carrito + cantidad_a_agregar):
                                        st.session_state.carrito.append({
                                            "id": pid,
                                            "nombre": item['nombre'],
                                            "cantidad": cantidad_a_agregar,
                                            "subtotal": subtotal,
                                            "es_peso": es_peso
                                        })
                                        st.success("¡Agregado!")
                                        st.rerun()
                                    else:
                                        st.error("¡No hay suficiente stock!")
                    st.write("")
            else:
                st.warning("No hay productos que coincidan con la búsqueda.")
        else:
            st.info("No hay productos cargados en el inventario.")

   # --- TAB 3: HISTORIAL / REPORTES ---
    with tab3:
        st.header("Historial de Ventas")
        
        # Botón para borrar TODO el historial
        if st.button("🗑️ Borrar TODO el historial"):
            ventas_todo = db.collection("ventas").stream()
            for v in ventas_todo:
                db.collection("ventas").document(v.id).delete()
            st.rerun()

        ventas_ref = db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
        
        for v in ventas_ref:
            data = v.to_dict()
            fecha = data['fecha'].strftime("%d/%m/%Y %H:%M")
            
            with st.expander(f"📅 {fecha} — Total: ${data['total']:.2f}"):
                for item in data.get('items', []):
                    st.write(f"- {item['nombre']} ({item['cantidad']:.2f}): ${item['subtotal']:.2f}")
                
                # Botón de borrar individual
                if st.button("❌ Eliminar esta venta", key=f"del_v_{v.id}"):
                    db.collection("ventas").document(v.id).delete()
                    st.rerun()
