import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_qrcode_scanner import qrcode_scanner
import json
from datetime import datetime, timedelta
from datetime import datetime

# --- CONFIGURACIÓN DE ROLES Y CONTRASEÑAS ---
CLAVE_PADRES = "1211"     # Acceso total (Productos, Ventas, Historial)
CLAVE_EMPLEADAS = "clave_empleadas_456" # Acceso limitado (Solo Ventas)

def check_password():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.rol = None
        
    if not st.session_state.autenticado:
        st.title("🛒 Negocio - Login")
        input_pass = st.text_input("Ingrese su contraseña para acceder:", type="password")
        
        if st.button("Acceder"):
            if input_pass == CLAVE_PADRES:
                st.session_state.autenticado = True
                st.session_state.rol = "padres"
                st.rerun()
            elif input_pass == CLAVE_EMPLEADAS:
                st.session_state.autenticado = True
                st.session_state.rol = "empleadas"
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

    # Botón para cerrar sesión y cambiar de usuario
    if st.sidebar.button("🔒 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.rol = None
        st.rerun()

    if "carrito" not in st.session_state:
        st.session_state.carrito = []

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

    # --- CONTROL DE VISTAS SEGÚN EL ROL ---
    if st.session_state.rol == "padres":
        tab1, tab2, tab3 = st.tabs(["📦 Productos", "💰 Ventas / Caja", "📊 Historial / Reportes"])
    else:
        # Las empleadas solo tienen acceso a la pestaña de ventas
        tab2 = st.tabs(["💰 Ventas / Caja"])[0]

    # --- TAB 1: PRODUCTOS (Solo Padres) ---
    if st.session_state.rol == "padres":
        with tab1:
            st.header("📦 Gestión de Inventario")

            with st.expander("➕ Agregar Nuevo Producto o Categoría"):
                col_nc1, col_nc2 = st.columns(2)
                
                with col_nc1:
                    st.subheader("Nuevo Producto")
                    usar_escaner_carga = st.checkbox("📷 Usar cámara para escanear código", key="chk_cam_inv")
                    codigo_detectado_carga = ""
                    
                    if usar_escaner_carga:
                        codigo_detectado_carga = qrcode_scanner(key="scanner_carga")
                        if codigo_detectado_carga:
                            st.success(f"¡Código leído: {codigo_detectado_carga}!")

                    codigo_nuevo = st.text_input("Código de barras", value=codigo_detectado_carga if codigo_detectado_carga else "", key="input_cod_nuevo")
                    nombre_nuevo = st.text_input("Nombre del producto", key="input_nom_nuevo")
                    cat_nueva = st.selectbox("Categoría", obtener_categorias(), key="cat_prod_nuevo")
                    precio_nuevo = st.number_input("Precio ($)", min_value=0.0, format="%.2f", key="precio_prod_nuevo")
                    stock_nuevo = st.number_input("Stock inicial", min_value=0.0, step=0.5, format="%.2f", key="stock_prod_nuevo")
                    n_minimo = st.number_input("Alerta de Stock Mínimo", min_value=0.0, value=5.0, step=0.5)

                    
                    imagen_nueva = st.text_input("URL de la imagen (Opcional)", key="input_img_nuevo", placeholder="https://ejemplo.com/foto.jpg")
                    if imagen_nueva.strip():
                        try:
                            st.image(imagen_nueva.strip(), width=250, caption="Vista previa")
                        except:
                            st.warning("No se pudo cargar la vista previa con esa URL.")
                    
                    if st.button("Guardar Producto", key="btn_save_prod"):
                        if nombre_nuevo:
                            db.collection("productos").add({
                                "nombre": nombre_nuevo, 
                                "codigo": codigo_nuevo.strip(),
                                "categoria": cat_nueva, 
                                "precio": precio_nuevo, 
                                "stock": stock_nuevo,
                                "stock_minimo": n_minimo,
                                "imagen": imagen_nueva.strip()
                            })
                            st.success("¡Producto guardado!")
                            st.rerun()
                        else:
                            st.error("Ingresa un nombre.")

                with col_nc2:
                    st.subheader("Gestión de Categorías")
                    nueva_cat = st.text_input("Nombre de categoría", key="input_nueva_cat_tab")
                    if st.button("Guardar Categoría", key="btn_save_cat"):
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
                                db.collection("categorias").document(cat['id']).delete()
                                st.success("Categoría borrada")
                                st.rerun()

            st.divider()
            st.subheader("Buscar y Filtrar Inventario")
            
            usar_esc_inv = st.checkbox("📷 Escanear código para buscar producto", key="chk_esc_inv")
            cod_escaneado = ""
            if usar_esc_inv:
                cod_escaneado = qrcode_scanner(key="scanner_inv")
                if cod_escaneado:
                    st.success(f"Código detectado: {cod_escaneado}")

            col_b1, col_b2 = st.columns(2)
            valor_busqueda = cod_escaneado if cod_escaneado else ""
            busqueda = col_b1.text_input("🔍 Buscar por nombre o código", value=valor_busqueda, key="busq_inv")
            opciones_filtro = ["Todas"] + obtener_categorias()
            filtro_cat = col_b2.selectbox("Filtrar por categoría", opciones_filtro, key="filt_inv_cat")

            productos_ref = db.collection("productos").stream()
            lista = [ {**p.to_dict(), "id": p.id} for p in productos_ref ]

            if busqueda:
                lista = [p for p in lista if busqueda.lower() in p['nombre'].lower() or busqueda.lower() in str(p.get('codigo', '')).lower()]
            if filtro_cat != "Todas":
                lista = [p for p in lista if p.get('categoria') == filtro_cat]

           if lista:
                st.write("Despliega cada producto para editar sus datos:")
                for item in lista:
                    codigo_txt = f" | Código: {item.get('codigo', 'Sin código')}" if item.get('codigo') else ""
                    
                    # --- NUEVO: LÓGICA DE ALERTA PARA EL TÍTULO ---
                    stock_act = float(item.get('stock', 0))
                    stock_min = float(item.get('stock_minimo', 5.0))
                    
                    if stock_act <= 0:
                        icono_alerta = "🔴 [SIN STOCK]"
                    elif stock_act <= stock_min:
                        icono_alerta = "🟡 [STOCK BAJO]"
                    else:
                        icono_alerta = "🟢"
                    # ---------------------------------------------
                    
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
                        # Añadimos el icono_alerta al principio del título del expander
                        titulo_acordeon = f"{icono_alerta} {item['nombre']} — ${item.get('precio', 0):.2f} | Stock: {stock_act}{codigo_txt} ({item.get('categoria', 'Sin categoría')})"
                        
                        with st.expander(titulo_acordeon):
                            if url_img:
                                try:
                                    st.image(url_img, width=250)
                                except:
                                    st.warning("No se pudo cargar la imagen.")

                            nombre_edit = st.text_input("Nombre", value=item['nombre'], key=f"n{item['id']}")
                            codigo_edit = st.text_input("Código de barras", value=item.get('codigo', ''), key=f"cod{item['id']}")
                            precio_edit = st.number_input("Precio / Valor Kilo", value=float(item.get('precio', 0)), key=f"p{item['id']}")
                            stock_edit = st.number_input("Stock", value=float(item.get('stock', 0)), step=0.5, format="%.2f", key=f"s{item['id']}")
                            minimo_edit = st.number_input("Stock Mínimo de Alerta", value=float(item.get('stock_minimo', 5.0)), step=0.5, key=f"min{item['id']}")
                            
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
                                    "stock_minimo": minimo_edit,
                                    "categoria": cat_edit,
                                    "imagen": imagen_edit.strip()
                                })
                                st.rerun()
                            if col2.button("Eliminar", key=f"del{item['id']}"):
                                db.collection("productos").document(item['id']).delete()
                                st.rerun()
                    st.write("")
            else:
                st.info("No hay productos cargados o que coincidan con la búsqueda.")

    # --- TAB 2: VENTAS / CAJA (CARRITO) ---
    with tab2:
        st.header("🛒 Caja / Carrito de Ventas")

        prods_ref = db.collection("productos").stream()
        productos_dict = {p.id: p.to_dict() for p in prods_ref}

        if productos_dict:
            # TICKET ARRIBA (Optimizado para Celular)
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
                                
                                stock_actual = float(item.get('stock', 0))
                                stock_minimo = float(item.get('stock_minimo', 5.0))

                                if stock_actual <= 0:
                                    st.error("❌ ¡SIN STOCK!")
                                elif stock_actual <= stock_minimo:
                                    st.warning(f"⚠️ STOCK BAJO: Quedan {stock_actual:.1f} (Mínimo: {stock_minimo})")
                                else:
                                    st.success(f"Stock disponible: {stock_actual:.1f}")

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

# --- TAB 3: HISTORIAL / REPORTES (Solo Padres) ---
    if st.session_state.rol == "padres":
        with tab3:
            st.header("📊 Reportes y Historial de Ventas")
            
            # --- SECCIÓN DE REPORTES / MÉTRICAS ---
            st.subheader("Resumen General")
            
            ventas_ref = db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
            
            total_historico = 0.0
            ventas_hoy = 0.0
            ventas_semana = 0.0
            ventas_mes = 0.0
            
            hoy = datetime.now()
            hoy_str = hoy.strftime("%Y-%m-%d")
            mes_actual_str = hoy.strftime("%Y-%m")
            inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            
            lista_completa = []
            
            for v in ventas_ref:
                data = v.to_dict()
                total_v = float(data.get('total', 0))
                total_historico += total_v
                
                f_obj = data.get('fecha')
                f_dt = f_obj.to_datetime() if hasattr(f_obj, 'to_datetime') else f_obj
                
                # Acumuladores de métricas
                if f_dt.strftime("%Y-%m-%d") == hoy_str: ventas_hoy += total_v
                if f_dt >= inicio_semana: ventas_semana += total_v
                if f_dt.strftime("%Y-%m") == mes_actual_str: ventas_mes += total_v
                    
                lista_completa.append({"id": v.id, "dt": f_dt, "total": total_v, "items": data.get('items', [])})

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("📅 Hoy", f"${ventas_hoy:.2f}")
            col_m2.metric("🗓️ Sem.", f"${ventas_semana:.2f}")
            col_m3.metric("📆 Mes", f"${ventas_mes:.2f}")
            col_m4.metric("💰 Total", f"${total_historico:.2f}")

            st.divider()

            # --- RANKING DE PRODUCTOS MÁS VENDIDOS ---
            st.subheader("🏆 Top 5 Productos más vendidos")
            
            ranking = {}
            for v in lista_completa:
                for item in v['items']:
                    nombre = item.get('nombre', 'Desconocido')
                    cantidad = float(item.get('cantidad', 0))
                    ranking[nombre] = ranking.get(nombre, 0) + cantidad
            
            if ranking:
                # Ordenamos el diccionario por cantidad de mayor a menor
                top_productos = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:5]
                
                # Mostramos el ranking de forma estilizada
                cols_rank = st.columns(len(top_productos))
                for i, (prod, cant) in enumerate(top_productos):
                    # Usamos una columna por producto para que se vea bien en fila
                    with cols_rank[i]:
                        st.metric(label=prod[:10] + "..." if len(prod) > 10 else prod, value=f"{cant:.1f}")
            else:
                st.info("Aún no hay suficientes datos para el ranking.")
            
            st.divider() # Separador antes del Detalle de Ventas
            # --- FILTRO Y LISTADO ---
            st.subheader("Detalle de Ventas")
            filtro_vista = st.selectbox("Filtrar historial por:", ["Todo el historial", "Solo HOY", "Solo esta SEMANA", "Solo este MES"], key="filtro_hist")

            if filtro_vista == "Solo HOY":
                lista_filtrada = [v for v in lista_completa if v['dt'].strftime("%Y-%m-%d") == hoy_str]
            elif filtro_vista == "Solo esta SEMANA":
                lista_filtrada = [v for v in lista_completa if v['dt'] >= inicio_semana]
            elif filtro_vista == "Solo este MES":
                lista_filtrada = [v for v in lista_completa if v['dt'].strftime("%Y-%m") == mes_actual_str]
            else:
                lista_filtrada = lista_completa

            if lista_filtrada:
                for v in lista_filtrada:
                    fecha_fmt = v['dt'].strftime("%d/%m/%Y %H:%M")
                    with st.expander(f"📅 {fecha_fmt} — Total: ${v['total']:.2f}"):
                        for item in v['items']:
                            st.write(f"- {item.get('nombre', 'Producto')} x {item.get('cantidad', 0):.2f} = **${item.get('subtotal', 0):.2f}**")
                        
                        if st.checkbox("Marcar para eliminar esta venta", key=f"del_{v['id']}"):
                            if st.button("❌ Confirmar eliminación", key=f"btn_{v['id']}"):
                                db.collection("ventas").document(v['id']).delete()
                                st.success("Venta eliminada")
                                st.rerun()
            else:
                st.info("No se encontraron ventas para el filtro seleccionado.")

            st.divider()
            # --- OPCIONES AVANZADAS ---
            with st.expander("⚙️ Opciones avanzadas"):
                if st.checkbox("⚠️ Habilitar borrado masivo", key="check_masivo"):
                    if st.button("🗑️ BORRAR TODO EL HISTORIAL"):
                        for v in lista_completa:
                            db.collection("ventas").document(v["id"]).delete()
                        st.success("Historial borrado.")
                        st.rerun()
                st.info("Aún no hay ventas registradas.")
