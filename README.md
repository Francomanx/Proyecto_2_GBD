## Proyecto_2_GBD
Base de Datos Activa

Integrantes:
- Franco Arenas
- Jeremi Arriagada


## Tablas

```sql
CREATE TABLE clientes (
cliente_id SERIAL PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
correo_electronico VARCHAR(100) UNIQUE NOT NULL,
telefono VARCHAR(20),
direccion VARCHAR(50),
fecha_nacimiento DATE NOT NULL,
rut VARCHAR(12) UNIQUE NOT NULL,
fecha_registro DATE NOT NULL,
CONSTRAINT rut_valido CHECK (rut ~ '^\d{7,8}-[\dkK]$'),
CONSTRAINT edad_valida CHECK (fecha_nacimiento <= '2007-06-04')
);
```
```sql
CREATE TABLE productos (
producto_id SERIAL PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
descripcion TEXT,
precio INTEGER NOT NULL,
stock INTEGER NOT NULL DEFAULT 0,
categoria VARCHAR(100),
activo BOOLEAN DEFAULT TRUE,
CONSTRAINT precio_valido CHECK (precio >= 0),
umbral_critico INTEGER DEFAULT 4 CHECK (umbral_critico >= 0)
);
```
```sql
CREATE TABLE personal(
    personal_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(50) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    activo BOOLEAN DEFAULT TRUE
);
```
```sql
CREATE TABLE pedidos (
    pedido_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    fecha_pedido DATE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    total INTEGER NOT NULL DEFAULT 0 CHECK (total >= 0),
    vendedor_id INTEGER REFERENCES personal(personal_id)
);
```
```sql
CREATE TABLE detalle_pedido (
    detalle_id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(producto_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario INTEGER NOT NULL CHECK (precio_unitario > 0),
	CONSTRAINT evitar_producto_duplicado UNIQUE (pedido_id, producto_id)
);
```
```sql
CREATE TABLE pago (
    pago_id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    fecha_pago DATE DEFAULT CURRENT_DATE,
    monto INTEGER NOT NULL CHECK (monto > 0),
    metodo_pago VARCHAR(50) NOT NULL CHECK (metodo_pago IN ('tarjeta', 'efectivo')),
    estado_pago VARCHAR(50) NOT NULL DEFAULT 'pendiente' CHECK (estado_pago IN ('pendiente', 'completado', 'rechazado'))
);
```
```sql
CREATE TABLE envios (
    envio_id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    distribuidor_id INT NOT NULL REFERENCES personal(personal_id) ON DELETE SET NULL,
    estado_envio VARCHAR(50) CHECK (estado_envio IN ('procesado', 'enviando', 'entregado')),
    fecha_envio DATE NOT NULL,
    fecha_entrega DATE,
    tracking VARCHAR(100) UNIQUE,
    CONSTRAINT verificar_fecha_envio_y_entrega CHECK (fecha_entrega IS NULL OR fecha_entrega >= fecha_envio)
);
```
```sql
CREATE TABLE auditoria_pedidos (
    auditoria_id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    estado_anterior VARCHAR(50) NOT NULL,
    estado_nuevo VARCHAR(50) NOT NULL,
    fecha_cambio DATE DEFAULT CURRENT_DATE,
    usuario_cambio INTEGER NOT NULL REFERENCES personal(personal_id)
);
```


## Orden para importar los datos
Considerar que {ruta} es donde se clono este repositorio (ej. ```'C:/Users/juan/Desktop'```)

- cliente
```sql
\copy clientes FROM '{ruta}/Proyecto_2_GBD/clientes_data.csv' DELIMITER ',' CSV HEADER
```
- productos
```sql
\copy productos FROM '{ruta}/Proyecto_2_GBD/productos_data.csv' DELIMITER ',' CSV HEADER
```
- personal
```sql
\copy personal FROM '{ruta}/Proyecto_2_GBD/personal_data.csv' DELIMITER ',' CSV HEADER
```
- pedidos
```sql
\copy pedidos FROM '{ruta}/Proyecto_2_GBD/pedido_data.csv' DELIMITER ',' CSV HEADER
```
- detalle_pedido
```sql
\copy detalle_pedido FROM '{ruta}/Proyecto_2_GBD/detalles_pedido_data.csv' DELIMITER ',' CSV HEADER
```
- pago
```sql
\copy pago FROM '{ruta}/Proyecto_2_GBD/pago_data.csv' DELIMITER ',' CSV HEADER
```
- envios
```sql
\copy envios FROM '{ruta}/Proyecto_2_GBD/envios_data.csv' DELIMITER ',' CSV HEADER
```
Y una vez que haya cargado los datos a las tablas puede usar los siguientes codigos para sincronizar el contador de ids
```sql
SELECT setval('clientes_cliente_id_seq', (SELECT MAX(cliente_id) FROM clientes));
SELECT setval('pedidos_pedido_id_seq', (SELECT MAX(pedido_id) FROM pedidos));
SELECT setval('detalle_pedido_detalle_id_seq', (SELECT MAX(detalle_id) FROM detalle_pedido));
SELECT setval('envios_envio_id_seq', (SELECT MAX(envio_id) FROM envios));
SELECT setval('pago_pago_id_seq', (SELECT MAX(pago_id) FROM pago));
SELECT setval('productos_producto_id_seq', (SELECT MAX(producto_id) FROM productos));
SELECT setval('personal_personal_id_seq', (SELECT MAX(personal_id) FROM personal));
```

## Procedimientos Almacenados
**A.- Calcular y actualizar el total del pedido**
```sql
CREATE FUNCTION calcular_total_de_pedido(id_pedido INTEGER)
RETURNS INTEGER AS $$
DECLARE
	monto_total INTEGER;
BEGIN
	SELECT 
		CASE 
    			WHEN SUM(detallito.cantidad * detallito.precio_unitario) IS NULL THEN 0
    			ELSE SUM(detallito.cantidad * detallito.precio_unitario)
		END
	INTO monto_total
	FROM detalle_pedido detallito
	WHERE detallito.pedido_id = id_pedido;
	UPDATE pedidos
	SET total = monto_total
	WHERE pedido_id = id_pedido;
	RETURN monto_total;
END;
$$ LANGUAGE 'plpgsql';
```
**B.- Registrar pago y verificar su validez**
```sql
--Procedimiento B. Registrar pago y verificar su validez
CREATE OR REPLACE PROCEDURE registrar_pago (id_pedido INTEGER, monto_pagar INTEGER, forma_pago VARCHAR(50))
LANGUAGE plpgsql
AS $$
DECLARE total_pedido INTEGER;
DECLARE estado_pedido VARCHAR(50);
BEGIN
	--Primero revisamos si la id entregada existe en la base de datos de pedidos
	SELECT total INTO total_pedido FROM pedidos WHERE pedidos.pedido_id = id_pedido;
	--Si no se encuentra se lanza una exception
	IF total_pedido IS NULL THEN
		RAISE EXCEPTION 'ERROR, el pedido que quieres pagar no presenta un costo o no existe en nuestra base de datos';
	END IF;
	--En el caso de que se haya encontrado, revisemos su estado
	SELECT estado INTO estado_pedido FROM pedidos WHERE pedidos.pedido_id = id_pedido;
	--Si un pedido tiene un estado diferente de pendiente, significa que esto ya esta pagado
	IF (estado_pedido != 'pendiente') THEN
		RAISE EXCEPTION 'ERROR, este pedido no presenta el estado pendiente, por ende, el pago ya fue realizado para este pedido';
	END IF;
	--Ahora vamos a ver si se puede pagar
	IF (total_pedido > monto_pagar)THEN
		RAISE EXCEPTION 'ERROR, el monto otorgado es menor a lo que hay que pagar';
	END IF;
	--Si se puede pagar, entonces registramos el pago
	--No sin antes verificar si el metodo de pago es valido para nuestro sistema
	IF (forma_pago != 'tarjeta' AND forma_pago != 'efectivo') THEN
		RAISE EXCEPTION 'ERROR, la forma de pago no es aceptada en nuestra base de datos (se recomienda solo uso de minusculas para declarar tu tipo de pago)';
	END IF;
	--Ahora si
	INSERT INTO pago (pedido_id, fecha_pago, monto, metodo_pago, estado_pago)
	VALUES (id_pedido, CURRENT_DATE, monto_pagar, forma_pago, 'completado');
	--Y actualizamos el estado de pendiente a procesado (en caso de que este pendiente)
	UPDATE pedidos
	SET estado = 'procesado' WHERE pedidos.pedido_id = id_pedido;
	RAISE NOTICE 'Pago registrado';
END;
$$;
```
**C.- Generar reporte mensual de ventas por vendedor**
```sql
CREATE OR REPLACE FUNCTION generar_reporte_ventas(mes INTEGER, anio INTEGER)
RETURNS TABLE (vendedor_id INTEGER,vendedor_nombre VARCHAR(100),cantidad_pedidos INTEGER,total_ventas INTEGER)
LANGUAGE plpgsql
AS $$ 
BEGIN
    RETURN QUERY
    SELECT vendedor.personal_id, 
           vendedor.nombre,
           CAST(COUNT(pedido.pedido_id) AS INTEGER),
           CAST(SUM(pedido.total) AS INTEGER)
    FROM pedidos pedido
    JOIN personal vendedor ON pedido.vendedor_id = vendedor.personal_id
    WHERE vendedor.rol = 'Vendedor'
      AND EXTRACT(MONTH FROM pedido.fecha_pedido) = mes
      AND EXTRACT(YEAR FROM pedido.fecha_pedido) = anio
    GROUP BY vendedor.personal_id, vendedor.nombre
    ORDER BY SUM(pedido.total) DESC;
END;
$$;
```
**D.- Generar informe de entregas por distribuidor**
```sql
CREATE OR REPLACE FUNCTION generar_informe_entregas_distribuidor()
RETURNS TABLE (distribuidor_id INTEGER,distribuidor_nombre VARCHAR(100),cantidad_entregas INTEGER)
LANGUAGE plpgsql
AS $$ 
BEGIN
    RETURN QUERY
    SELECT distribuidor.personal_id, distribuidor.nombre, CAST(COUNT(envio.envio_id) AS INTEGER)
    FROM envios envio
    INNER JOIN personal distribuidor ON envio.distribuidor_id = distribuidor.personal_id
    WHERE distribuidor.rol = 'Distribuidor' AND envio.estado_envio = 'entregado'
    GROUP BY distribuidor.personal_id, distribuidor.nombre
    ORDER BY COUNT(envio.envio_id) DESC;
END;
$$;
```
**E.- Enviar notificaciones de actualización de estado de pedido a los clientes**
```sql
CREATE OR REPLACE PROCEDURE notificar_actualizacion_de_estado_cliente (id_cliente INTEGER)
LANGUAGE plpgsql
AS $$
DECLARE nombre_cliente VARCHAR(100);
DECLARE antiguo_estado VARCHAR(50);
DECLARE nuevo_estado VARCHAR(50);
DECLARE id_pedido_actual INTEGER;
BEGIN
	--Primero podriamos buscar si el cliente a buscar existe en nuestra base de datos
	IF NOT EXISTS (SELECT 1 FROM clientes WHERE clientes.cliente_id = id_cliente) THEN
		RAISE EXCEPTION 'ERROR: la id ingresada no esta presente en nuestra base de datos';
	END IF;
	--En el caso de que esto no ocurra, significa que existe
	SELECT nombre into nombre_cliente FROM clientes WHERE clientes.cliente_id = id_cliente;
	--Tengo pensado ahora recorrer la lista de pedidos que tengan presente la id del cliente para luego
	--usar esta lista en donde buscaremos si cada una de estas ids presenta algun dato en auditoria_pedidos
	--Usando siempre el ULTIMO CAMBIO realizado al pedido
	FOR id_pedido_actual IN
		SELECT pedido_id FROM pedidos WHERE cliente_id = id_cliente
	LOOP
		SELECT estado_anterior INTO antiguo_estado FROM auditoria_pedidos WHERE auditoria_pedidos.pedido_id = id_pedido_actual
		ORDER BY fecha_cambio DESC --Si usamos esto obtenemos la ultima vez que se realizo un cambio a dicho pedido
		LIMIT 1;
		SELECT estado_nuevo INTO nuevo_estado FROM auditoria_pedidos WHERE auditoria_pedidos.pedido_id = id_pedido_actual
		ORDER BY fecha_cambio DESC --Si usamos esto obtenemos la ultima vez que se realizo un cambio a dicho pedido
		LIMIT 1;
		--Si se logra encontrar un dato presente en auditoria_pedidos, significa que el pedido si puede ser notificado al cliente
		--con comprobar que uno no sea null basta
		IF antiguo_estado IS NOT NULL THEN 
			RAISE NOTICE '%, Tu pedido con id % Tuvo un cambio de estado: de % a %',nombre_cliente,id_pedido_actual,antiguo_estado,nuevo_estado;
		END IF;
	END LOOP;
END;
$$;
```
**F.- Actualizar umbrales de stock critico por producto**
```sql
CREATE OR REPLACE PROCEDURE actualizar_umbral_critico(id_producto INTEGER, nuevo_umbral_critico INTEGER)
LANGUAGE plpgsql AS $$
DECLARE viejo_umbral_critico INTEGER;
BEGIN
	--Primero verificamos si el id del producto existe
	IF NOT EXISTS (
		SELECT 1 FROM productos WHERE productos.producto_id = id_producto  
	)THEN
		RAISE EXCEPTION 'ERROR, la id escrita del producto no se encuentra presente en nuestra base de datos';
	END IF;
	--Si existe, verificamos si el valor del umbral es el adecuado
	IF (nuevo_umbral_critico<0) THEN
		RAISE EXCEPTION 'ERROR, el nuevo umbral no cumple con las reglas impuestas por la base de datos (debe ser un numero positivo)';
	END IF;
	--Verificamos si el nuevo umbral tiene el mismo valor que antes
	SELECT umbral_critico INTO viejo_umbral_critico FROM productos WHERE productos.producto_id = id_producto;
	IF (viejo_umbral_critico = nuevo_umbral_critico) THEN
		RAISE NOTICE 'el nuevo valor del umbral es el mismo que el anterior, por ende es un cambio innecesario';
		RETURN;
	END IF;
	--Una vez hecha las verificaciones, pasamos a editarlo
	UPDATE productos
	SET umbral_critico = nuevo_umbral_critico
	WHERE productos.producto_id = id_producto;
	RAISE NOTICE 'Umbral critico editado';
END;
$$;
```
**(EXTRA) G.- Actualizar estado de un pedido (Solo los administradores pueden hacerlo)**
```sql
--el procedure va a pedir el id del pedido, junto con el nuevo estado que se le quiera dar, y el id_del personal para verificar si es administrador o non
CREATE OR REPLACE PROCEDURE actualizar_estado_pedido(id_pedido INTEGER, nuevo_estado VARCHAR(50), id_personal INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    --verificamos si el personal no existe. En el caso de que no, se llama la excepcion para mostrar el error en el output
    IF NOT EXISTS (
        SELECT * FROM personal WHERE personal_id = id_personal AND rol = 'Administrador' and activo = TRUE
    ) THEN
        RAISE EXCEPTION 'ERROR, solo los administradores o personal administrador activo pueden realizar cambios de estados';
    END IF;
    --si la excepcion no se llama, significa que podemos pasar a la siguiente verificacion
	--ahora verificamos si el id del pedido no existe en nuestra base de datos
	IF NOT EXISTS (
		SELECT * FROM pedidos WHERE pedido_id = id_pedido
	) THEN
		RAISE EXCEPTION 'ERROR, el pedido ingresado no existe en nuestros datos';
	END IF;
	--ahora si ninguna de estas excepciones se activaron, significa que podemos actualizar nuestro pedido

	-- el id del personal se puede guardar en una session. En caso de que un trigger necesite informacion adicional, los sessions 
	PERFORM set_config('session.usuario_cambio', id_personal::TEXT, FALSE);
    UPDATE pedidos SET estado = nuevo_estado WHERE pedido_id = id_pedido;
END;
$$;
```


## Triggers
**A.- Descontar stock al insertar un detalle_pedido**
```sql
CREATE OR REPLACE FUNCTION descontar_stock_producto()
RETURNS TRIGGER AS $$
DECLARE stock_producto INTEGER;
BEGIN
	--Buscamos el valor stock del producto a restar
	SELECT stock INTO stock_producto FROM productos WHERE productos.producto_id = NEW.producto_id;
	--Y hacemos una condicional para ver si se puede descontar o non
	IF stock_producto < NEW.cantidad THEN
		RAISE EXCEPTION 'ERROR, el stock del producto no es suficiente para el registro del detalle del pedido';
	END IF;
	--En el caso de que el stock es suficiente
	UPDATE productos
	SET stock = stock - NEW.cantidad
	WHERE productos.producto_id = NEW.producto_id;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_descontar_stock
BEFORE INSERT ON detalle_pedido
FOR EACH ROW
EXECUTE FUNCTION descontar_stock_producto();
```
**B.- Registrar cambios de estado del pedido en Auditoria_Pedidos**

Se hizo tanto el trigger como la funcion asociada al proceso de insercion del cambio de estado en uditoria_pedidos
```sql
CREATE OR REPLACE FUNCTION actualizar_auditoria_pedido()
RETURNS TRIGGER AS $$
DECLARE id_personal INT;
BEGIN
    --Verificamos si el estado realmente es diferente del anterior, sino no vale la pena agregarlo a la base de datos
    IF OLD.estado != NEW.estado THEN
		--obtenemos el id del personal en la session
		SELECT current_setting('session.usuario_cambio')::INTEGER INTO id_personal;
        INSERT INTO auditoria_pedidos (pedido_id, estado_anterior, estado_nuevo, fecha_cambio, usuario_cambio)
        VALUES (NEW.pedido_id, OLD.estado, NEW.estado, CURRENT_DATE, id_personal);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_actualizacion_auditoria_pedido
AFTER UPDATE ON pedidos
FOR EACH ROW
EXECUTE FUNCTION actualizar_auditoria_pedido();
```
**C.- Registrar inicio de proceso de envio cuando cambia de estado a 'procesado'**
```sql
CREATE OR REPLACE FUNCTION registrar_inicio_de_proceso_envio()
RETURNS TRIGGER AS $$
DECLARE id_repartidor INTEGER;
DECLARE codigo_tracking TEXT;
BEGIN
	--verificamos el estado del pedido para ver si paso a ser procesado o no. En caso de, tambien vale revisar si el estado procesado ya lo tuvo
	IF NEW.estado = 'procesado' AND OLD.estado != 'procesado' THEN
		--Si resulta estar procesado buscamos un repartidor al azar
		SELECT personal_id INTO id_repartidor FROM personal WHERE rol = 'Distribuidor' AND activo = TRUE
		ORDER BY RANDOM() LIMIT 1;

		--En caso de que no hayan repartidores disponibles
		IF id_repartidor IS NULL THEN
			RAISE EXCEPTION 'ERROR, en este momento no hay distribuidores disponibles';
		END IF;

		--En caso de que si haya un repartidor elegido, entonces se empieza a hacer registro del envio en la tabla
		--No sin antes hacer el codigo del tracking
		--El proceso de la creacion del codigo consiste en sacar los ultimos 8 caracteres de la derecha de la cadena aleatoria unica de md5()
		codigo_tracking := RIGHT(md5(random()::text), 8);
		INSERT INTO envios(pedido_id, distribuidor_id, estado_envio, fecha_envio, tracking)
		VALUES (NEW.pedido_id, id_repartidor, 'enviando', CURRENT_DATE, codigo_tracking);
	END IF;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_iniciar_envio
AFTER UPDATE ON pedidos
FOR EACH ROW
EXECUTE FUNCTION registrar_inicio_de_proceso_envio();
```
**D.- Disparar una notificación automática al cliente cada vez que cambie el estado del pedido o del envío. (100% COMPLETO)**
```sql
-- Trigger SOLO PARA CAMBIO DE ESTADO DEL PEDIDO, hay que hacer otro para el envio, pero para eso hay que hacer un procedure que cambie el estado de un envio
CREATE OR REPLACE FUNCTION notificar_cambio_estado_pedido_a_usuario()
RETURNS TRIGGER AS $$
BEGIN
    --Si el estado cambio, entonces toca notificar
    IF NEW.estado != OLD.estado THEN
        RAISE NOTICE 'Cliente Numero %, Su Pedido % ha cambiado de estado a: %', NEW.cliente_id, NEW.pedido_id, NEW.estado;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_notificacion_cambio_pedido_usuario
AFTER UPDATE ON pedidos
FOR EACH ROW
EXECUTE FUNCTION notificar_cambio_estado_pedido_a_usuario();
```
```sql
CREATE OR REPLACE FUNCTION notificar_cambio_estado_envio_a_cliente()
RETURNS TRIGGER AS $$
DECLARE id_cliente INT;
BEGIN
    --Primero buscamos al cliente asociado al envio del pedido
    SELECT pedidito.cliente_id INTO id_cliente
    FROM pedidos pedidito
    WHERE pedidito.pedido_id = NEW.pedido_id;

    --verificamos si el estado del envío cambió
    IF NEW.estado_envio != OLD.estado_envio THEN
        RAISE NOTICE 'Cliente Numero %, su pedido % ha cambiado el estado de su envio a: %', id_cliente, NEW.pedido_id, NEW.estado_envio;
    END IF;
    --si es que ahora esta entregado, añadimos un valor a fecha_entrega
    IF OLD.estado_envio = 'enviando' AND NEW.estado_envio = 'entregado' THEN
  	NEW.fecha_entrega := CURRENT_DATE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_notificacion_cambio_envio_cliente
BEFORE UPDATE ON envios
FOR EACH ROW
EXECUTE FUNCTION notificar_cambio_estado_envio_a_cliente();

```
**E.- Bloquear eliminación de clientes con pedidos activos.**
```sql
--Bloquear eliminacion de clientes con pedidos activos
--Voy a considerar 'activo' como aquellos pedidos que tiene cualquier estado menos 'entregado'
CREATE OR REPLACE FUNCTION verificar_eliminacion_cliente()
RETURNS TRIGGER AS $$
BEGIN
	--para este caso sale bueno usar un if not exist
	IF EXISTS (
		SELECT 1 FROM pedidos WHERE OLD.cliente_id = pedidos.cliente_id AND pedidos.estado != 'entregado'
	) THEN
		RAISE EXCEPTION 'ERROR, el cliente no se puede eliminar dado a que tiene pedidos activos';
	END IF;
	-- si la excepcion no se llama, significa que el cliente no tiene pedidos activos y se procede a eliminar
	RAISE NOTICE 'Se ha eliminado el usuario';
	RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_bloquear_eliminacion_cliente
BEFORE DELETE ON clientes
FOR EACH ROW
EXECUTE FUNCTION verificar_eliminacion_cliente();
```
**F.- Prevenir asignacion de pedidos a personal no registrado o activo O A PERSONAL QUE NO SEA VENDEDOR**
```sql
--Prevenir asignacion de pedidos a personal no registrado o inactivo
CREATE OR REPLACE FUNCTION verificar_asignacion_pedido()
RETURNS TRIGGER AS $$
DECLARE actividad BOOLEAN;
DECLARE rols VARCHAR(50);
BEGIN
	--esto va a estar basado en la insercion de un pedido, entonces de por si ahi
	--tenemos la id del personal
	SELECT activo INTO actividad FROM personal WHERE personal.personal_id = NEW.vendedor_id;
	IF (actividad != TRUE) THEN
		RAISE EXCEPTION 'ERROR, el personal asignado no esta activo';
	END IF;
	--APROVECHAMOS DE HACER OTRA VERIFICACION SI EL PERSONAL ES UN VENDEDOR O NON
	SELECT rol INTO rols FROM personal WHERE personal.personal_id = NEW.vendedor_id;
	IF (rols != 'Vendedor') THEN
		RAISE EXCEPTION 'ERROR, el personal asignado no es un vendedor, DEBE SERLO';
	END IF;
	
	--en el caso de que no haya saltado la excepction, significa que se puede insertar
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_verificar_asignacion_pedido
BEFORE INSERT ON pedidos
FOR EACH ROW
EXECUTE FUNCTION verificar_asignacion_pedido();
```
**G. Detectar cuando el stock de un producto cae por debajo de un umbral definido y registrar esta condición como "stock crítico"**
```sql
--Detectar cuando el stock de un producto cae por debajo de un umbral definido
--y registrar esta condicion como "stock critico"
CREATE OR REPLACE FUNCTION detectar_stock_critico()
RETURNS TRIGGER AS $$
BEGIN
	--Si el stock nuevo es menor al umbral, se lanza el mensaje y ya esta
	IF (NEW.stock <= NEW.umbral_critico) THEN
		RAISE NOTICE 'El stock del producto % recientemente usado presenta un stock CRITICO: % unidades restantes',NEW.producto_id, NEW.stock;
	END IF;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_stock_critico
AFTER UPDATE ON productos
FOR EACH ROW
EXECUTE FUNCTION detectar_stock_critico();
```

## Vistas
**A.- Historial_Cliente: Muestra todos los pedidos y pagos por cliente.**
```sql
CREATE VIEW Historial_Cliente AS
SELECT 
    c.cliente_id,
    c.nombre AS nombre_cliente,
    c.correo_electronico,
    p.pedido_id,
    p.fecha_pedido,
    p.estado AS estado_pedido,
    p.total AS total_pedido,
    pg.pago_id,
    pg.fecha_pago,
    pg.monto,
    pg.metodo_pago,
    pg.estado_pago
FROM clientes c
INNER JOIN pedidos p ON c.cliente_id = p.cliente_id
LEFT JOIN pago pg ON p.pedido_id = pg.pedido_id
ORDER BY c.cliente_id, p.fecha_pedido DESC;
```

**B.- Productos_Bajo_Stock: Productos con stock crítico.**

Se definio que menos de 5 elementos se considera un stock critico
```sql
CREATE VIEW Productos_Bajo_Stock AS
SELECT 
    producto_id,
    nombre,
    categoria,
    stock,
    precio
FROM productos
WHERE stock <= umbral_critico AND activo = true;
```

**C.- Seguimiento_Envios: Consulta de pedidos, estados de envío y responsables.**
```sql
CREATE VIEW Seguimiento_Envios AS
SELECT 
	p.pedido_id,
	p.fecha_pedido,
	perV.nombre AS responsable_venta,
	e.envio_id,
	e.estado_envio,
	e.fecha_envio,
	e.fecha_entrega,
	perD.nombre AS responsable_envio
FROM pedidos p
JOIN envios e ON p.pedido_id = e.pedido_id
LEFT JOIN personal perD ON e.distribuidor_id = perD.personal_id
LEFT JOIN personal perV ON p.vendedor_id = perV.personal_id
ORDER BY p.pedido_id DESC;
```

**D.- Ventas_Por_Vendedor: Muestra totales por personal de ventas.**
```sql
CREATE VIEW Ventas_Por_Vendedor AS
SELECT 
    per.personal_id,
    per.nombre AS nombre_vendedor,
    COUNT(p.pedido_id) AS cantidad_pedidos,
    SUM(p.total) AS total_ventas
FROM personal per
JOIN pedidos p ON per.personal_id = p.vendedor_id
GROUP BY per.personal_id, per.nombre
ORDER BY total_ventas DESC;
```

**E.- Entregas_Por_Distribuidor: Listado de entregas por distribuidor.**
```sql
CREATE VIEW Entregas_Por_Distribuidor AS
SELECT 
    per.personal_id,
    per.nombre AS nombre_distribuidor,
    COUNT(e.envio_id) AS entregas_realizadas,
    MAX(e.fecha_entrega) AS ultima_entrega
FROM personal per
JOIN envios e ON per.personal_id = e.distribuidor_id
WHERE e.estado_envio = 'entregado'
GROUP BY per.personal_id, per.nombre
ORDER BY entregas_realizadas DESC;
```

**F.- Notificaciones_Cliente: Historial de notificaciones enviadas a clientes.**
```sql
CREATE VIEW Notificaciones_Cliente AS
SELECT 
    c.cliente_id,
    c.nombre AS nombre_cliente,
    c.correo_electronico,
    p.pedido_id,
    a.estado_anterior,
    a.estado_nuevo,
    a.fecha_cambio,
    'Cambio de estado del pedido' AS tipo_notificacion
FROM auditoria_pedidos a
JOIN pedidos p ON a.pedido_id = p.pedido_id
JOIN clientes c ON p.cliente_id = c.cliente_id
ORDER BY a.fecha_cambio DESC;
```

**G.- Alerta_Stock_Critico: Productos con stock por debajo del umbral mínimo.**
```sql
CREATE VIEW Alerta_Stock_Critico AS
SELECT 
    producto_id,
    nombre,
    categoria,
    stock,
    precio,
    'Stock por debajo del mínimo crítico' AS alerta
FROM productos
WHERE stock <= umbral_critico AND activo = true;
```


## Funciones y Reglas
**A.- validar_rut_chileno(rut VARCHAR(12)): Verifica formato y dígito verificador.**
```sql
CREATE OR REPLACE FUNCTION validar_rut_chileno(rut VARCHAR(12))
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$ 
BEGIN
    RETURN rut ~ '^[0-9]{7,8}-[0-9Kk]$';
END;
$$;
```
**B.- es_mayor_edad(fecha_nacimiento DATE): Retorna TRUE si el cliente es mayor de 18 años.**
```sql
CREATE OR REPLACE FUNCTION es_mayor_edad(fecha_nacimiento DATE)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$ 
BEGIN
    RETURN AGE(fecha_nacimiento) >= INTERVAL '18 years';
END;
$$;
```
**C. es_stock_critico(producto_id INT): Retorna TRUE si el stock actual es menor o igual al umbral definido para ese producto.**
```sql
CREATE OR REPLACE FUNCTION es_stock_critico(id_producto INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE critico_umbral INTEGER;
DECLARE stock_producto INTEGER;
BEGIN
	--primero verificamos que el stock exista
	IF NOT EXISTS(SELECT producto_id FROM productos WHERE productos.producto_id = id_producto) THEN
		RAISE EXCEPTION 'ERROR, el producto no existe';
	END IF;
	--Ahora que lo encontramos verificamos si su stock presenta estado critico o no
	SELECT umbral_critico INTO critico_umbral FROM productos WHERE productos.producto_id = id_producto;
	SELECT stock INTO stock_producto FROM productos WHERE productos.producto_id = id_producto;
	RETURN stock_producto <= critico_umbral;
END;
$$;
```
## Casos de Prueba
**Esta seccion se re-edito puesto que el documento tiene experimentos y pruebas con una mejor documentacion. Aqui solamente se dejaran los Scripts y consultas para verificar los experimentos con mayor facilidad mientras se lee el informe**

**1.- Funcionalidad Correcta de Procedimiento para Cambiar Estado de Pedido y Trigger para Insertar Cambios de Estado en auditoria_pedidos.**

```sql
CALL actualizar_estado_pedido(75,'entregado',8);
```
```sql
CALL actualizar_estado_pedido(9,'entregado',7);
```
```sql
CALL actualizar_estado_pedido(1,'pendiente',8);
```
```sql
CALL actualizar_estado_pedido(1,'procesado',8);)
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado G
- Trigger B
- Trigger C
- Trigger D (50%)

**2.- Funcionalidad del Descuento de Stock.**

```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (5,1,2,280000);
```
```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (1,1,16,280000);
```

Con este experimento se confirma el funcionamiento de:
- Trigger A

**3.- Funcionalidad de Notificación de Cambio de Estado de Envío.**

```sql
UPDATE envios
SET estado_envios = 'entregado'
WHERE pedido_id = 1;
```

Con este experimento se confirma el funcionamiento de:
- Trigger D (100%)

**4.- Funcionalidad para Evitar Eliminar Cliente con Pedidos Activos.**

```sql
DELETE FROM clientes WHERE cliente_id = 28;
```
```sql
DELETE FROM clientes WHERE cliente_id = 35;
```

Con este experimento se confirma el funcionamiento de:
- Trigger E

**5.- Funcionalidad para Evitar Asignar Pedidos a Personal Inexistente o Inactiva.**

```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id)
VALUES (99, 'pendiente', 2);
```
```sql
UPDATE personal
SET activo = FALSE
WHERE personal_id = 2;
```
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id)
VALUES (1, 'pendiente', 2);
```
```sql
UPDATE personal
SET activo = TRUE
WHERE personal_id = 2;
```
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id)
VALUES (1, 'pendiente', 2);
```
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id)
VALUES (2, 'pendiente', 1);
```

Con este experimento se confirma el funcionamiento de:
- Trigger F

**6.- Funcionalidad para Mostrar Mensaje de Stock Crítico.**

```sql
UPDATE productos SET stock = 3 WHERE producto_id = 5;
```

Con este experimento se confirma el funcionamiento de:
- Trigger G

**7.- Funcionalidad para Registrar Pago de un Pedido Pendiente.**

```sql
CALL registrar_pago(99, 5000, 'tarjeta');
```
```sql
CALL registrar_pago(1, 589980, 'tarjeta');
```
```sql
CALL registrar_pago(2, 1000, 'tarjeta');
```
```sql
CALL registrar_pago(2, 377940, 'francodolares');
```
```sql
CALL registrar_pago(2, 377940, 'tarjeta');
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado B

**8.- Funcionalidad para Imprimir la Tabla de Ganancias Mensuales de Vendedores.**

```sql
SELECT * FROM generar_reporte_ventas(6,2025);
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado C

**9.- Funcionalidad para Imprimir las Entregas Realizadas por Cada Distribuidor.**

```sql
SELECT * FROM generar_informe_entregas_distribuidor();
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado D

**10.- Funcionalidad para Cambiar el Valor del Umbral Crítico por Producto.**

```sql
CALL actualizar_umbral_critico(12,6);
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado F

**11.- Funcionalidad para Verificar Envío de Notificaciones a Usuarios Respecto a los Cambios de Estado de sus Pedidos.**

```sql
CALL notificar_actualizacion_de_estado_cliente(38);
```

Con este experimento se confirma el funcionamiento de:
- Procedimiento Almacenado E

**12.- Funcionalidad para Validar un rut Chileno.**

```sql
SELECT validar_rut_chileno('21045981-2');
```
```sql
SELECT validar_rut_chileno('21.045.982.1');
```

Con este experimento se confirma el funcionamiento de:
- Funcion A

**13.- Funcionalidad para Verificar la edad con Base en una Fecha**

```sql
SELECT es_mayor_edad('2002-09-08');
```
```sql
SELECT es_mayor_edad('2020-01-01');
```

Con este experimento se confirma el funcionamiento de:
- Funcion B

**14.- Funcionalidad para Preguntar Stock Crítico de un Producto.**

```sql
SELECT es_stock_critico(105);
```
```sql
SELECT es_stock_critico(1);
```
```sql
SELECT es_stock_critico(5);
```

Con este experimento se confirma el funcionamiento de:
- Funcion C
