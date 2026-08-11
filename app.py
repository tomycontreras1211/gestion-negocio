import streamlit as str_lib
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

    st.title("🛒 Negocio Familiar - Gestión Integral")

    # Pestañas principales
    tab1, tab2, tab3 = st.tabs(["📦 Productos", "💰 Ventas", "📊 Historial / Reportes"])

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
                precio_nuevo = st.number_input("Precio ($) [Precio unitario o valor del Kilo]", min_value=0.0, format="%.2f", key="precio_prod_nuevo")
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

    # --- TAB 2: VENTAS UNIFICADA ---
    with tab2:
        st.header("Caja / Registrar Venta")
        
        prods_ref = db.collection("productos").stream()
        productos_dict = {p.id: p.to_dict() for p in prods_ref}

        if productos_dict:
            # Opción rápida de escáner arriba del todo
            usar_esc = st.checkbox("📷 Usar escáner de cámara para venta rápida")
            producto_activo_id = None
            producto_activo_data = None

            if usar_esc:
                codigo_escaneado = qrcode_scanner(key="scanner_ventas_unificado")
                if codigo_escaneado:
                    for pid, d in productos_dict.items():
                        if str(d.get('codigo', '')).strip() == str(codigo_escaneado).strip():
                            producto_activo_id = pid
                            producto_activo_data = d
                            break
                    if not producto_activo_data:
                        st.warning("Código leído pero no encontrado en el inventario.")

            # Si no usó escáner (o quiere buscar por nombre/categoría)
            if not producto_activo_data:
                st.write("--- O busca el producto manualmente ---")
                col_f1, col_f2 = st.columns(2)
                busq_v = col_f1.text_input("🔍 Buscar por nombre o código", key="busq_uni")
                cat_v = col_f2.selectbox("Filtrar categoría", ["Todas"] + obtener_categorias(), key="cat_uni")

                filtrados = {}
                for pid, d in productos_dict.items():
                    c_nom = not busq_v or busq_v.lower() in d['nombre'].lower() or busq_v.lower() in str(d.get('codigo', '')).lower()
                    c_cat = cat_v == "Todas" or d.get('categoria') == cat_v
                    if c_nom and c_cat:
                        filtrados[pid] = d

                if filtrados:
                    opciones = [f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}" for pid, d in filtrados.items()]
                    mapa_ids = {f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}": pid for pid, d in filtrados.items()}
                    
                    seleccion_prod = st.selectbox("Selecciona un producto", opciones, key="sel_uni")
                    producto_activo_id = mapa_ids[seleccion_prod]
                    producto_activo_data = productos_dict[producto_activo_id]
                else:
                    st.warning("No hay productos con esos filtros.")

            # Si ya tenemos un producto activo (por escáner o selección manual), mostramos su tarjeta y opciones de venta adaptadas
            if producto_activo_data:
                st.divider()
                col_i1, col_i2 = st.columns([1, 2])
                
                with col_i1:
                    if producto_activo_data.get('imagen'):
                        try:
                            st.image(producto_activo_data.get('imagen'), width=180)
                        except:
                            pass
                
                with col_i2:
                    st.subheader(producto_activo_data['nombre'])
                    st.write(f"**Categoría:** {producto_activo_data.get('categoria', 'Sin categoría')}")
                    st.write(f"**Precio base / Kilo:** ${producto_activo_data.get('precio', 0)}")
                    st.write(f"**Stock actual:** {producto_activo_data.get('stock', 0)}")

                st.write("---")
                
                # DETECCIÓN AUTOMÁTICA DE TIPO DE VENTA SEGÚN LA CATEGORÍA O PRECIO
                # (Si pertenece a Panadería o querés manejar decimales por peso, podés validarlo aquí o dar opción fluida)
                es_por_peso = st.checkbox("⚖️ Es una venta por peso / monto libre (ej. Pan, Fiambre)", key="check_peso_auto")

                precio_unitario = float(producto_activo_data.get('precio', 0))
                stock_actual = float(producto_activo_data.get('stock', 0))

                if not es_por_peso:
                    # Venta normal por unidades
                    cant = st.number_input("Cantidad a vender (Unidades)", min_value=1.0, step=1.0, value=1.0, key="cant_uni_v")
                    total_pagar = precio_unitario * cant
                    st.info(f"Total a cobrar: **${total_pagar:.2f}**")

                    if st.button("✅ Confirmar Venta", key="btn_conf_uni"):
                        if stock_actual >= cant:
                            db.collection("productos").document(producto_activo_id).update({"stock": stock_actual - cant})
                            st.success(f"¡Venta registrada! Stock restante: {stock_actual - cant}")
                        else:
                            st.error("¡No hay suficiente stock disponible!")
                else:
                    # Venta por peso o monto exacto de dinero
                    sub_modo = st.radio("¿Cómo se calcula?", ["Por Gramos / Kilos", "Por Dinero exacto ($)"], key="sub_modo_peso")
                    
                    if sub_modo == "Por Gramos / Kilos":
                        kilos = st.number_input("Kilos (Ej: 0.5 para 500g, 1 para 1kg)", min_value=0.01, value=0.5, step=0.1, format="%.3f", key="kilos_v")
                        total_pagar = precio_unitario * kilos
                        st.info(f"Total a cobrar: **${total_pagar:.2f}**")

                        if st.button("✅ Confirmar Venta por Peso", key="btn_conf_peso"):
                            if stock_actual >= kilos:
                                db.collection("productos").document(producto_activo_id).update({"stock": stock_actual - kilos})
                                st.success(f"¡Venta registrada! Stock restante: {stock_actual - kilos:.3f} kg")
                            else:
                                st.error("¡No hay suficiente stock!")
                    else:
                        dinero = st.number_input("Dinero que entrega el cliente ($)", min_value=1.0, value=500.0, step=50.0, key="dinero_v")
                        if precio_unitario > 0:
                            kilos_calc = dinero / precio_unitario
                            st.info(f"Equivale a: **{kilos_calc * 1000:.0f} gramos** ({kilos_calc:.3f} kg)")

                            if st.button("✅ Confirmar Venta por Dinero", key="btn_conf_dinero"):
                                if stock_actual >= kilos_calc:
                                    db.collection("productos").document(producto_activo_id).update({"stock": stock_actual - kilos_calc})
                                    st.success(f"¡Venta registrada! Se descontaron {kilos_calc:.3f} kg.")
                                else:
                                    st.error("¡No hay suficiente stock!")
                        else:
                            st.error("Este producto tiene precio $0.")
        else:
            st.info("No hay productos cargados en el inventario.")

    # --- TAB 3: HISTORIAL / REPORTES ---
    with tab3:
        st.header("Historial y Reportes")
        st.info("Aquí podrás ver el registro de ventas diarias próximamente.")
