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

    # Inicializar el carrito en la sesión
    if "carrito" not in st.session_state:
        st.session_state.carrito = []

    # Pestañas principales
    tab1, tab2, tab3 = st.tabs(["📦 Productos", "💰 Ventas / Caja", "📊 Historial / Reportes"])

    # --- FUNCIONES DE APOYO ---
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

    # --- TAB 1: PRODUCTOS ---
    with tab1:
        st.header("Inventario de Productos")

        with st.expander("➕ Agregar Nuevo Producto o Categoría"):
            col_nc1, col_nc2 = st.columns(2)
            
            with col_nc1:
                st.subheader("Nuevo Producto")
                usar_escaner_carga = st.checkbox("📷 Usar cámara para escanear código")
                codigo_detectado_carga = ""
                
                if usar_escaner_carga:
                    codigo_detectado_carga = qrcode_scanner(key="scanner_carga")
                    if codigo_detectado_carga:
                        st.success(f"¡Código leído: {codigo_detectado_carga}!")

                codigo_nuevo = st.text_input("Código de barras", value=codigo_detectado_carga if codigo_detectado_carga else "", key="input_cod_nuevo")
                nombre_nuevo = st.text_input("Nombre del producto", key="input_nom_nuevo")
                cat_nueva = st.selectbox("Categoría", obtener_categorias(), key="cat_prod_nuevo")
                precio_nuevo = st.number_input("Precio ($) [Unitario o valor del Kilo]", min_value=0.0, format="%.2f", key="precio_prod_nuevo")
                stock_nuevo = st.number_input("Stock inicial", min_value=0.0, step=0.5, format="%.2f", key="stock_prod_nuevo")
                
                imagen_nueva = st.text_input("URL de la imagen (Opcional)", key="input_img_nuevo", placeholder="https://ejemplo.com/foto.jpg")
                if imagen_nueva.strip():
                    try:
                        st.image(imagen_nueva.strip(), width=250, caption="Vista previa")
                    except:
                        st.warning("No se pudo cargar la vista previa con esa URL.")
                
                if st.button("Guardar Producto"):
                    if nombre_nuevo:
                        db.collection("productos").add({
                            "nombre": nombre_nuevo, 
                            "codigo": codigo_nuevo.strip(),
                            "categoria": cat_nueva, 
                            "precio": precio_nuevo, 
                            "stock": stock_nuevo,
                            "imagen": imagen_nueva.strip()
                        })
                        st.success("¡Producto guardado!")
                        st.rerun()
                    else:
                        st.error("Ingresa un nombre.")

            with col_nc2:
                st.subheader("Gestión de Categorías")
                nueva_cat = st.text_input("Nombre de categoría", key="input_nueva_cat_tab")
                if st.button("Guardar Categoría"):
                    if nueva_cat:
                        cats_actuales = [c.lower() for c in obtener_categorias()]
                        if nueva_cat.strip().lower() in cats_actuales:
                            st.warning("Esa categoría ya existe.")
                        else:
                            db.collection("categorias").add({"nombre": nueva_cat.strip()})
                            st.success("¡Categoría guardada!")
                            st.rerun()

                st.write("---")
                st.write("Categorías existentes:")
                cats_existentes = obtener_categorias_con_id()
                if cats_existentes:
                    for cat in cats_existentes:
                        col_c1, col_c2 = st.columns([2, 1])
                        col_c1.write(cat["nombre"])
                        if col_c2.button("Borrar", key=f"del_cat_{cat['id']}"):
                            db.collection("categorias").document(cat["id"]).delete()
                            st.success("Categoría borrada")
                            st.rerun()

        st.divider()
        
        col_b1, col_b2 = st.columns(2)
        busqueda = col_b1.text_input("🔍 Buscar por nombre o código")
        opciones_filtro = ["Todas"] + obtener_categorias()
        filtro_cat = col_b2.selectbox("Filtrar por categoría", opciones_filtro)

        productos_ref = db.collection("productos").stream()
        lista = [ {**p.to_dict(), "id": p.id} for p in productos_ref ]

        if busqueda:
            lista = [p for p in lista if busqueda.lower() in p['nombre'].lower() or busqueda.lower() in str(p.get('codigo', '')).lower()]
        if filtro_cat != "Todas":
            lista = [p for p in lista if p.get('categoria') == filtro_cat]

        if lista:
            for item in lista:
                codigo_txt = f" | Código: {item.get('codigo', 'Sin código')}" if item.get('codigo') else ""
                
                with st.expander(f"{item['nombre']} — ${item.get('precio', 0):.2f} | Stock: {item.get('stock', 0)}{codigo_txt} ({item.get('categoria', 'Sin categoría')})"):
                    url_img = item.get('imagen', '')
                    if url_img:
                        try:
                            st.image(url_img, width=250)
                        except:
                            st.warning("No se pudo cargar la imagen.")

                    nombre_edit = st.text_input("Nombre", value=item['nombre'], key=f"n{item['id']}")
                    codigo_edit = st.text_input("Código de barras", value=item.get('codigo', ''), key=f"cod{item['id']}")
                    precio_edit = st.number_input("Precio / Valor Kilo", value=float(item.get('precio', 0)), key=f"p{item['id']}")
                    stock_edit = st.number_input("Stock", value=float(item.get('stock', 0)), step=0.5, format="%.2f", key=f"s{item['id']}")
                    
                    imagen_edit = st.text_input("URL de la imagen", value=item.get('imagen', ''), key=f"img{item['id']}")
                    if imagen_edit.strip():
                        try:
                            st.image(imagen_edit.strip(), width=200, caption="Vista previa")
                        except:
                            pass
                    
                    cats_disp = obtener_categorias()
                    cat_idx = cats_disp.index(item.get('categoria')) if item.get('categoria') in cats_disp else 0
                    cat_edit = st.selectbox("Categoría", cats_disp, index=cat_idx, key=f"c{item['id']}")
                    
                    col1, col2 = st.columns(2)
                    if col1.button("Actualizar", key=f"upd{item['id']}"):
                        db.collection("productos").document(item['id']).update({
                            "nombre": nombre_edit, 
                            "codigo": codigo_edit.strip(),
                            "precio": precio_edit, 
                            "stock": stock_edit,
                            "categoria": cat_edit,
                            "imagen": imagen_edit.strip()
                        })
                        st.rerun()
                    if col2.button("Eliminar", key=f"del{item['id']}"):
                        db.collection("productos").document(item['id']).delete()
                        st.rerun()
        else:
            st.info("No hay productos cargados o que coincidan con la búsqueda.")

    # --- TAB 2: VENTAS / CAJA (CARRITO) ---
    with tab2:
        st.header("🛒 Caja / Carrito de Ventas")

        prods_ref = db.collection("productos").stream()
        productos_dict = {p.id: p.to_dict() for p in prods_ref}

        if productos_dict:
            col_izq, col_der = st.columns([1.2, 0.8])

            with col_izq:
                st.subheader("Agregar productos al ticket")
                
                # Opción de escáner rápido
                usar_esc = st.checkbox("📷 Usar escáner para agregar al carrito")
                prod_seleccionado_id = None
                prod_seleccionado_data = None

                if usar_esc:
                    codigo_escaneado = qrcode_scanner(key="scanner_carrito")
                    if codigo_escaneado:
                        for pid, d in productos_dict.items():
                            if str(d.get('codigo', '')).strip() == str(codigo_escaneado).strip():
                                prod_seleccionado_id = pid
                                prod_seleccionado_data = d
                                break
                        if not prod_seleccionado_data:
                            st.warning("Código leído pero no encontrado en el inventario.")

                if not prod_seleccionado_data:
                    col_f1, col_f2 = st.columns(2)
                    busq_v = col_f1.text_input("🔍 Buscar producto", key="busq_cart")
                    cat_v = col_f2.selectbox("Filtrar categoría", ["Todas"] + obtener_categorias(), key="cat_cart")

                    filtrados = {}
                    for pid, d in productos_dict.items():
                        c_nom = not busq_v or busq_v.lower() in d['nombre'].lower() or busq_v.lower() in str(d.get('codigo', '')).lower()
                        c_cat = cat_v == "Todas" or d.get('categoria') == cat_v
                        if c_nom and c_cat:
                            filtrados[pid] = d

                    if filtrados:
                        opciones = [f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}" for pid, d in filtrados.items()]
                        mapa_ids = {f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}": pid for pid, d in filtrados.items()}
                        
                        seleccion_prod = st.selectbox("Seleccionar producto", opciones, key="sel_cart")
                        prod_seleccionado_id = mapa_ids[seleccion_prod]
                        prod_seleccionado_data = productos_dict[prod_seleccionado_id]
                    else:
                        st.warning("No hay productos con esos filtros.")

                if prod_seleccionado_data:
                    st.write("---")
                    col_img, col_det = st.columns([1, 2])
                    with col_img:
                        if prod_seleccionado_data.get('imagen'):
                            try:
                                st.image(prod_seleccionado_data.get('imagen'), width=120)
                            except:
                                pass
                    with col_det:
                        st.write(f"**{prod_seleccionado_data['nombre']}**")
                        st.write(f"Precio base/kilo: ${prod_seleccionado_data.get('precio', 0)}")
                        st.write(f"Stock disponible: {prod_seleccionado_data.get('stock', 0)}")

                    # Definir cantidad o peso a agregar
                    es_peso = st.checkbox("⚖️ Es por peso / monto (ej. Pan, Fiambre)", key="chk_peso_add")
                    precio_b = float(prod_seleccionado_data.get('precio', 0))

                    cantidad_a_agregar = 1.0
                    subtotal = 0.0

                    if not es_peso:
                        cantidad_a_agregar = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0, key="cant_add_uni")
                        subtotal = precio_b * cantidad_a_agregar
                    else:
                        sub_op = st.radio("Cálculo por peso:", ["Gramos / Kilos", "Dinero exacto ($)"], key="sub_op_cart")
                        if sub_op == "Gramos / Kilos":
                            cantidad_a_agregar = st.number_input("Kilos (Ej: 0.5 para 500g)", min_value=0.01, value=0.5, step=0.1, format="%.3f", key="kg_add")
                            subtotal = precio_b * cantidad_a_agregar
                        else:
                            dinero_ing = st.number_input("Dinero ($)", min_value=1.0, value=500.0, step=50.0, key="din_add")
                            if precio_b > 0:
                                cantidad_a_agregar = dinero_ing / precio_b
                                subtotal = dinero_ing
                            else:
                                cantidad_a_agregar = 0.0
                                subtotal = 0.0

                    if st.button("➕ Agregar al Carrito"):
                        # Revisar si hay stock suficiente considerando lo que ya está en el carrito
                        stock_actual = float(prod_seleccionado_data.get('stock', 0))
                        en_carrito = sum([item['cantidad'] for item in st.session_state.carrito if item['id'] == prod_seleccionado_id])
                        
                        if stock_actual >= (en_carrito + cantidad_a_agregar):
                            st.session_state.carrito.append({
                                "id": prod_seleccionado_id,
                                "nombre": prod_seleccionado_data['nombre'],
                                "cantidad": cantidad_a_agregar,
                                "subtotal": subtotal,
                                "es_peso": es_peso
                            })
                            st.success("¡Agregado al ticket!")
                            st.rerun()
                        else:
                            st.error("¡No hay suficiente stock disponible para agregar más!")

            with col_der:
                st.subheader("🧾 Ticket Actual")
                if st.session_state.carrito:
                    total_general = 0
                    for i, item in enumerate(st.session_state.carrito):
                        unidad_txt = "kg" if item['es_peso'] else "unid."
                        st.write(f"**{item['nombre']}** ({item['cantidad']:.3f} {unidad_txt}) — **${item['subtotal']:.2f}**")
                        total_general += item['subtotal']
                        if st.button("❌ Quitar", key=f"quitar_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()

                    st.divider()
                    st.markdown(f"### Total a Pagar: ${total_general:.2f}")

                    col_c1, col_c2 = st.columns(2)
                    if col_c1.button("✅ Confirmar Venta Total"):
                        # Descontar stock de Firestore para cada producto del carrito
                        stock_ok = True
                        for item in st.session_state.carrito:
                            p_ref = db.collection("productos").document(item['id'])
                            p_data = p_ref.get().to_dict()
                            if p_data:
                                nuevo_stock = float(p_data.get('stock', 0)) - item['cantidad']
                                p_ref.update({"stock": nuevo_stock})

                        st.success("¡Venta registrada con éxito y stock actualizado!")
                        st.session_state.carrito = []
                        st.rerun()

                    if col_c2.button("🗑️ Vaciar Carrito"):
                        st.session_state.carrito = []
                        st.rerun()
                else:
                    st.info("El carrito está vacío.")
        else:
            st.info("No hay productos cargados en el inventario.")

    # --- TAB 3: HISTORIAL / REPORTES ---
    with tab3:
        st.header("Historial y Reportes")
        st.info("Aquí podrás ver el registro de ventas diarias próximamente.")
