import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_qrcode_scanner import qrcode_scanner

# Inicializar Firebase directamente tomando todos los secretos como un diccionario
if not firebase_admin._apps:
    cred_dict = dict(st.secrets)
    cred = credentials.Certificate(cred_dict)
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
        lista = ["Bebidas", "Lácteos", "Almacén", "Limpieza"]
    return lista

def obtener_categorias_con_id():
    cat_ref = db.collection("categorias").stream()
    lista = []
    for c in cat_ref:
        data = c.to_dict()
        lista.append({"id": c.id, "nombre": data.get("nombre")})
    return sorted(lista, key=lambda x: x["nombre"])

# --- BARRA LATERAL: GESTIÓN RÁPIDA (Izquierda) ---
with st.sidebar:
    st.header("➕ Agregar Producto")
    
    # Escáner opcional para el código de barras al cargar
    usar_escaner_carga = st.checkbox("📷 Usar cámara para escanear código")
    codigo_detectado_carga = ""
    
    if usar_escaner_carga:
        st.write("Apunta al código del producto nuevo:")
        codigo_detectado_carga = qrcode_scanner(key="scanner_carga")
        if codigo_detectado_carga:
            st.success(f"¡Código leído: {codigo_detectado_carga}!")

    # El campo de texto se llena solo si se escanea, o se puede escribir a mano
    codigo_nuevo = st.text_input("Código de barras", value=codigo_detectado_carga if codigo_detectado_carga else "")
    
    nombre_nuevo = st.text_input("Nombre del producto")
    cat_nueva = st.selectbox("Categoría", obtener_categorias(), key="cat_sidebar")
    precio_nuevo = st.number_input("Precio ($)", min_value=0.0, format="%.2f")
    stock_nuevo = st.number_input("Stock inicial", min_value=0, step=1)
    
    if st.button("Guardar Producto"):
        if nombre_nuevo:
            db.collection("productos").add({
                "nombre": nombre_nuevo, 
                "codigo": codigo_nuevo.strip(),
                "categoria": cat_nueva, 
                "precio": precio_nuevo, 
                "stock": stock_nuevo
            })
            st.success("¡Producto guardado!")
            st.rerun()
        else:
            st.error("Ingresa un nombre.")

    st.divider()

    st.header("⚙️ Gestión de Categorías")
    
    with st.expander("➕ Nueva Categoría"):
        nueva_cat = st.text_input("Nombre de categoría", key="input_nueva_cat")
        if st.button("Guardar Categoría"):
            if nueva_cat:
                cats_actuales = [c.lower() for c in obtener_categorias()]
                if nueva_cat.strip().lower() in cats_actuales:
                    st.warning("Esa categoría ya existe.")
                else:
                    db.collection("categorias").add({"nombre": nueva_cat.strip()})
                    st.success("¡Categoría guardada!")
                    st.rerun()

    with st.expander("🗑️ Borrar Categorías"):
        cats_existentes = obtener_categorias_con_id()
        if cats_existentes:
            for cat in cats_existentes:
                col_c1, col_c2 = st.columns([2, 1])
                col_c1.write(cat["nombre"])
                if col_c2.button("Borrar", key=f"del_cat_{cat['id']}"):
                    db.collection("categorias").document(cat["id"]).delete()
                    st.success("Categoría borrada")
                    st.rerun()
        else:
            st.info("No hay categorías creadas.")

# --- TAB 1: PRODUCTOS (Inventario Principal) ---
with tab1:
    st.header("Inventario de Productos")
    
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
                nombre_edit = st.text_input("Nombre", value=item['nombre'], key=f"n{item['id']}")
                codigo_edit = st.text_input("Código de barras", value=item.get('codigo', ''), key=f"cod{item['id']}")
                precio_edit = st.number_input("Precio", value=float(item.get('precio', 0)), key=f"p{item['id']}")
                stock_edit = st.number_input("Stock", value=int(item.get('stock', 0)), key=f"s{item['id']}")
                
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
                        "categoria": cat_edit
                    })
                    st.rerun()
                if col2.button("Eliminar", key=f"del{item['id']}"):
                    db.collection("productos").document(item['id']).delete()
                    st.rerun()
    else:
        st.info("No hay productos cargados o que coincidan con la búsqueda.")

# --- TAB 2: VENTAS (Con Escáner de Cámara) ---
with tab2:
    st.header("Registrar Venta con Cámara")
    
    st.write("Apunta con la cámara del celular al código de barras del producto:")
    codigo_escaneado = qrcode_scanner(key="scanner_ventas")
    
    prods_ref = db.collection("productos").stream()
    productos_dict = {p.id: p.to_dict() for p in prods_ref}
    
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
            st.warning("El código fue leído, pero no está asociado a ningún producto cargado. Agrégalo en el inventario.")

    if producto_encontrado_data:
        st.info(f"**Producto:** {producto_encontrado_data['nombre']} | **Precio:** ${producto_encontrado_data.get('precio', 0)} | **Stock actual:** {producto_encontrado_data.get('stock', 0)}")
        cant_vender = st.number_input("Cantidad a vender", min_value=1, step=1, value=1, key="cant_escaneada")
        
        if st.button("Confirmar Venta Escaneada"):
            stock_actual = int(producto_encontrado_data.get('stock', 0))
            if stock_actual >= cant_vender:
                db.collection("productos").document(producto_encontrado_id).update({"stock": stock_actual - cant_vender})
                st.success(f"¡Venta registrada con éxito! Stock restante: {stock_actual - cant_vender}")
            else:
                st.error("¡No hay suficiente stock disponible!")
    
    st.write("---")
    st.subheader("O seleccionar manualmente:")
    if productos_dict:
        seleccion = st.selectbox("Seleccionar producto", [f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}" for p_id, d in productos_dict.items()])
        cant_vender_man = st.number_input("Cantidad", min_value=1, step=1, key="cant_manual")
        
        if st.button("Confirmar Venta Manual"):
            p_id = [pid for pid, d in productos_dict.items() if f"{d['nombre']} (${d.get('precio', 0)}) - Stock: {d.get('stock', 0)}" == seleccion][0]
            data = productos_dict[p_id]
            stock_actual = int(data.get('stock', 0))
            
            if stock_actual >= cant_vender_man:
                db.collection("productos").document(p_id).update({"stock": stock_actual - cant_vender_man})
                st.success(f"¡Venta registrada! Stock restante: {stock_actual - cant_vender_man}")
            else:
                st.error("¡No hay suficiente stock disponible!")

# --- TAB 3: HISTORIAL / REPORTES ---
with tab3:
    st.header("Historial y Reportes")
    st.info("Aquí podrás ver el registro de ventas diarias próximamente.")
