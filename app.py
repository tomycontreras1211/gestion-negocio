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
                precio_nuevo = st.number_input("Precio ($) [O valor del Kilo]", min_value=0.0, format="%.2f", key="precio_prod_nuevo")
                stock_nuevo = st.number_input("Stock inicial", min_value=0.0, step=0.5, format="%.2f", key="stock_prod_nuevo")
                
                imagen_nueva = st.text_input("URL de la imagen (Opcional)", key="input_img_nuevo", placeholder="https://ejemplo.com/foto.jpg")
                if imagen_nueva.strip():
                    try:
                        st.image(imagen_nueva.strip(), width=100, caption="Vista previa")
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
                
                # Diseño en columnas para mostrar la miniatura directo en la lista desplegable/encabezado
                with st.container():
                    col_img_list, col_txt_list = st.columns([1, 6])
                    
                    with col_img_list:
                        url_img = item.get('imagen', '')
                        if url_img:
                            try:
                                st.image(url_img, width=50)
                            except:
                                st.write("🖼️")
                        else:
                            st.write("📦")
                            
                    with col_txt_list:
                        with st.expander(f"{item['nombre']} — ${item.get('precio', 0):.2f} | Stock: {item.get('stock', 0)}{codigo_txt} ({item.get('categoria', 'Sin categoría')})"):
                            
                            if url_img:
                                try:
                                    st.image(url_img, width=150)
                                except:
                                    pass

                            nombre_edit = st.text_input("Nombre", value=item['nombre'], key=f"n{item['id']}")
                            codigo_edit = st.text_input("Código de barras", value=item.get('codigo', ''), key=f"cod{item['id']}")
                            precio_edit = st.number_input("Precio / Valor Kilo", value=float(item.get('precio', 0)), key=f"p{item['id']}")
                            stock_edit = st.number_input("Stock", value=float(item.get('stock', 0)), step=0.5, format="%.2f", key=f"s{item['id']}")
                            
                            imagen_edit = st.text_input("URL de la imagen", value=item.get('imagen', ''), key=f"img{item['id']}")
                            if imagen_edit.strip():
                                try:
                                    st.image(imagen_edit.strip(), width=100, caption="Vista previa edición")
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
                st.write("") # Pequeño espacio entre productos
        else:
            st.info("No hay productos cargados o que coincidan con la búsqueda.")

    # --- TAB 2: VENTAS ---
    with tab2:
        st.header("Registrar Venta")
        
        tipo_venta = st.radio("¿Cómo deseas realizar la venta?", ["📷 Con Escáner de Cámara", "📋 Selección Manual (Unidades)", "⚖️ Venta por Peso / Suelto (Ej: Pan)"])
        
        prods_ref = db.collection("productos").stream()
        productos_dict = {p.id: p.to_dict() for p in prods_ref}

        # 1. ESCÁNER
        if tipo_venta == "📷 Con Escáner de Cámara":
            st.write("Apunta con la cámara del celular al código de barras del producto:")
            codigo_escaneado = qrcode_scanner(key="scanner_ventas")
            
            producto_encontrado_id = None
            producto_encontrado_data = None

            if codigo_escaneado:
                st.success(f"¡Código detectado: {codigo_escaneado}!")
                for pid, d in productos_dict.items():
                    if str(d.get('codigo', '')).strip() == str(codigo_escaneado).strip():
                        producto_encontrado_id = pid
                        producto_encontrado_data = d
                        break
                
                if not producto_encontrado_data:
                    st.warning("El código fue leído, pero no está asociado a ningún producto cargado.")

            if producto_encontrado_data:
                if producto_encontrado_data.get('imagen'):
                    try:
                        st.image(producto_encontrado_data.get('imagen'), width=120)
                    except:
                        pass
                st.info(f"**Producto:** {producto_encontrado_data['nombre']} | **Precio:** ${producto_encontrado_data.get('precio', 0)} | **Stock actual:** {producto_encontrado_data.get('stock', 0)}")
                cant_vender = st.number_input("Cantidad a vender", min_value=1.0, step=1.0, value=1.0, key="cant_escaneada")
                
                if st.button("Confirmar Venta Escaneada"):
                    stock_actual = float(producto_encontrado_data.get('stock', 0))
                    if stock_actual >= cant_vender:
                        db.collection("productos").document(producto_encontrado_id).update({"stock": stock_actual - cant_vender})
                        st.success(f"¡Venta registrada con éxito! Stock restante: {stock_actual - cant_vender}")
                    else:
                        st.error("¡No hay suficiente stock disponible!")

        # 2. SELECCIÓN MANUAL (UNIDADES)
        elif tipo_venta == "📋 Selección Manual (Unidades)":
            if productos_dict:
                opciones_productos = []
                mapa_opciones = {}
                for p_id, d in productos_dict.items():
                    texto_opcion = f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}"
                    opciones_productos.append(texto_opcion)
                    mapa_opciones[texto_opcion] = p_id
                
                seleccion = st.selectbox("Seleccionar producto", opciones_productos, key="select_manual_venta")
                
                p_id_temp = mapa_opciones[seleccion]
                img_temp = productos_dict[p_id_temp].get('imagen', '')
                if img_temp:
                    try:
                        st.image(img_temp, width=100)
                    except:
                        pass

                cant_vender_man = st.number_input("Cantidad", min_value=1.0, step=1.0, key="cant_manual", value=1.0)
                
                if st.button("Confirmar Venta Manual"):
                    p_id_elegido = p_id_temp
                    data = productos_dict[p_id_elegido]
                    stock_actual = float(data.get('stock', 0))
                    
                    if stock_actual >= cant_vender_man:
                        db.collection("productos").document(p_id_elegido).update({"stock": stock_actual - cant_vender_man})
                        st.success(f"¡Venta registrada! Stock restante: {stock_actual - cant_vender_man}")
                    else:
                        st.error("¡No hay suficiente stock disponible!")
            else:
                st.info("No hay productos cargados en el inventario.")

        # 3. VENTA POR PESO / SUELTO
        elif tipo_venta == "⚖️ Venta por Peso / Suelto (Ej: Pan)":
            if productos_dict:
                opciones_peso = []
                mapa_peso = {}
                for p_id, d in productos_dict.items():
                    texto_op = f"{d['nombre']} (Valor Kilo: ${d.get('precio', 0)})"
                    opciones_peso.append(texto_op)
                    mapa_peso[texto_op] = p_id

                sel_peso = st.selectbox("Seleccionar producto por peso", opciones_peso, key="select_peso_venta")
                
                p_id_peso = mapa_peso[sel_peso]
                datos_prod = productos_dict[p_id_peso]
                
                if datos_prod.get('imagen'):
                    try:
                        st.image(datos_prod.get('imagen'), width=100)
                    except:
                        pass

                modo_calculo = st.radio("¿Cómo querés calcular la venta?", ["Ingresar Gramos / Kilos a llevar", "Ingresar Dinero exacto ($) que paga"])
                
                precio_kilo = float(datos_prod.get('precio', 0))

                if modo_calculo == "Ingresar Gramos / Kilos a llevar":
                    cantidad_kg = st.number_input("Cantidad en Kilos (Ej: 0.5 para 500g, 1 para 1kg)", min_value=0.01, value=0.5, step=0.1, format="%.3f")
                    total_a_cobrar = precio_kilo * cantidad_kg
                    st.write(f"### Total a cobrar: **${total_a_cobrar:.2f}**")
                    
                    if st.button("Confirmar Venta por Peso"):
                        stock_actual = float(datos_prod.get('stock', 0))
                        if stock_actual >= cantidad_kg:
                            db.collection("productos").document(p_id_peso).update({"stock": stock_actual - cantidad_kg})
                            st.success(f"¡Venta registrada! Total cobrado: ${total_a_cobrar:.2f}. Stock restante: {stock_actual - cantidad_kg:.3f} kg")
                        else:
                            st.error("¡No hay suficiente stock en la base de datos!")

                else:
                    dinero_dado = st.number_input("¿Cuánto dinero paga el cliente? ($)", min_value=1.0, value=500.0, step=50.0)
                    if precio_kilo > 0:
                        kilos_calculados = dinero_dado / precio_kilo
                        st.write(f"Equivale a: **{kilos_calculados * 1000:.0f} gramos** ({kilos_calculados:.3f} kg)")
                        
                        if st.button("Confirmar Venta por Dinero"):
                            stock_actual = float(datos_prod.get('stock', 0))
                            if stock_actual >= kilos_calculados:
                                db.collection("productos").document(p_id_peso).update({"stock": stock_actual - kilos_calculados})
                                st.success(f"¡Venta registrada! Se descontaron {kilos_calculados:.3f} kg del stock.")
                            else:
                                st.error("¡No hay suficiente stock en la base de datos!")
                    else:
                        st.error("Este producto tiene precio $0, así que no se puede calcular.")
            else:
                st.info("No hay productos cargados en el inventario.")

    # --- TAB 3: HISTORIAL / REPORTES ---
    with tab3:
        st.header("Historial y Reportes")
        st.info("Aquí podrás ver el registro de ventas diarias próximamente.")
