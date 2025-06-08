## Proyecto_2_GBD
Insertar Descriptción


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
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id),
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
    pedido_id INT NOT NULL REFERENCES pedidos(pedido_id),
    fecha_pago DATE DEFAULT CURRENT_DATE,
    monto INTEGER NOT NULL CHECK (monto > 0),
    metodo_pago VARCHAR(50) CHECK (metodo_pago IN ('tarjeta', 'efectivo')),
    estado_pago VARCHAR(50) CHECK (estado_pago IN ('pendiente', 'completado', 'rechazado'))
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


## Procedures y (Funciones)
**A.- Calcular y actualizar el total del pedido**
me acabo de dar cuenta que un procedure tambien estaria bueno, pero esto igual funciona
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
--no sabia que se podia comentar waos
--el procedure va a pedir el id del pedido, junto con el nuevo estado que se le quiera dar, y el id_del personal para verificar si es administrador o non
CREATE OR REPLACE PROCEDURE actualizar_estado_pedido(id_pedido INTEGER, nuevo_estado VARCHAR(50), id_personal INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    --verificamos si el personal no existe. En el caso de que no, se llama la excepcion para mostrar el error en el output
    IF NOT EXISTS (
        SELECT * FROM personal WHERE personal_id = id_personal AND rol = 'Administrador'
    ) THEN
        RAISE EXCEPTION 'ERROR, solo los administradores pueden realizar cambios de estados';
    END IF;
    --si la excepcion no se llama, significa que podemos pasar a la siguiente verificacion
	--ahora verificamos si el id del pedido no existe en nuestra base de datos
	IF NOT EXISTS (
		SELECT * FROM pedidos WHERE pedido_id = id_pedido
	) THEN
		RAISE EXCEPTION 'ERROR, el pedido ingresado no existe en nuestros datos';
	END IF;
	--ahora si ninguna de estas excepciones gritonearon, significa que podemos actualizar nuestro pedido

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
		SELECT personal_id INTO id_repartidor FROM personal WHERE rol = 'Distribuidor'
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
-- Trigger SOLO PARA CAMBIO DE ESTADO DEL PEDIDO, hay que hacer otro para el envio, pero para eso hay que hacer un procedure que cambie el estado de un envio pipipi
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

    -- Verificar si el estado del envío cambió
    IF NEW.estado_envio != OLD.estado_envio THEN
        RAISE NOTICE 'Cliente Numero %, su pedido % ha cambiado el estado de su envio a: %', id_cliente, NEW.pedido_id, NEW.estado_envio;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_notificacion_cambio_envio_cliente
AFTER UPDATE ON envios
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
consideremos hacer uno para actualizar el precio unitario de los productos en detalle_pedido. La idea que tengo es que el precio unitario de detalle_pedido deberia tener el mismo valor que presenta al producto que referencia a traves de producto_id. En el faker es facil de hacer pero nose como referenciarlo a traves de sql, asi que creo que toco hacer un trigger adicional pipipi


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
WHERE stock < 5 AND activo = true;
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

**E.- Entregas_Por_Distribuidor: Listado de entregas por distribuidor.**
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

**F.- Notificaciones_Cliente: Historial de notificaciones enviadas a clientes.**
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

**G.- Alerta_Stock_Critico: Productos con stock por debajo del umbral mínimo.**
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


## Funciones y Reglas


## Casos de Prueba
**Prueba numero 1: Funcionalidad correcta de Procedure G y Trigger B**

Se supone que con esto, a la hora de querer cambiar de estado, hay que verificar dos cosas, siendo estas que el id del personal corresponda a un administrador y que la id del producto se encuentre presente en la base de datos
Probemos la primera excepcion
```sql
CALL actualizar_estado_pedido(75,'entregado',8);
```
Esto deberia dar error en la segunda verificacion:
```sql
ERROR:  ERROR, el pedido ingresado no existe en nuestros datos
CONTEXT:  función PL/pgSQL actualizar_estado_pedido(integer,character varying,integer) en la línea 14 en RAISE 

SQL state: P0001
```
EXITO... Sigamos adelante, ahora usemos un id de un pedido que si existe en la base, pero esta vez vamos a usar una id de un personal que NO es 'Administrador':
```sql
CALL actualizar_estado_pedido(9,'entregado',7);
```
Esto deberia dar error en la primer verificacion:
```sql
ERROR:  ERROR, solo los administradores pueden realizar cambios de estados
CONTEXT:  función PL/pgSQL actualizar_estado_pedido(integer,character varying,integer) en la línea 7 en RAISE 

SQL state: P0001
```
EXITO... ahora usemos un id de un pedido que si existe en la base y una id de un personal que si es administrador, pero cambiemoslo por el mismo estado. Esto NO deberia ingresar nada en la tabla auditoria_pedidos
```sql
CALL actualizar_estado_pedido(1,'pendiente',8);
```
Segun nuestros csv's, el primer pedido ya tiene el estado pendiente, por ende, el procedure deberia funcionar, pero no agregar nada a la tabla auditoria_pedido:
```sql
CALL

Query returned successfully in 105 msec.
```
Bueno, no cacho como mandar un mensaje para que me diga que no se añadio nada xd, pero me meti a la tabla y en efecto no hay nada de nada.....EXITOOOOOOOOO c r e o. YA LA ULTIMA PRUEBA, QUE TODO FUNCIONE. eso si, si se prueba hay que restaurar las tablas porque al no tener ciertos procedures y triggers hechos, voy a infringir un coso respecto a la tabla de envios. en vez de cambiar el estado al mismo, ahora pasara de estar de pendiente a procesado:
```sql
CALL actualizar_estado_pedido(1,'procesado',8);
```
Este cambio deberia de verse registrado en la tabla de auditoria_pedidos, veamos:
```sql
CALL
```
SE LOGROOOOOOOOOOO

**Prueba Numero 2: El stock se descuenta (Trigger A)**
Se supone que con esto, a la hora de agregar un detalle_producto, se va a realizar el calculo de stock - cantidad al producto referenciado. Esto tiene unas verificaciones por supuesto, aunque ahora que lo pienso existe la posibilidad de que al agregar el detalle del pedido, puedes colocar el precio unitario a 0, y creo que eso es un problemon. mmmm vamos a probar algo

```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (5, 1, 2, 280000);
```
Vamos a insertar un detalle a un pedido que existe y con un stock valido. Si comparan el csv con la base de datos del postgre, podemos ver que en efecto, al producto 1 que tenia 15 de stock se le resta 2 quedando con 13 de stock. EXITO... por ahora. Hubo un problema con el contador de serial keys? tuve que intentar poner el insert varias veces hasta que llego al contador 30 (hay 30 detalles ingresados en el sistema). Voy a ver si esto se puede solucionar mas adelante para evitar este tipo de errores.

Ahora me gustaria insertar un detalle_pedido de un pedido que no existe:
```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (25, 1, 2, 280000);
```
Se supone que deberia haber un error, al no existir un pedido que tenga id 25
```sql
ERROR:  La llave (pedido_id)=(25) no está presente en la tabla «pedidos».inserción o actualización en la tabla «detalle_pedido» viola la llave foránea «detalle_pedido_pedido_id_fkey» 

ERROR:  inserción o actualización en la tabla «detalle_pedido» viola la llave foránea «detalle_pedido_pedido_id_fkey»
SQL state: 23503
Detail: La llave (pedido_id)=(25) no está presente en la tabla «pedidos».
```
Muy bien, ahora la penultima prueba. Vamos a insertar un detalle_pedido de un pedido que existe y un producto que no existe:
```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (5, 90, 1, 25000);
```
Esto deberia de dar error:
```sql
ERROR:  La llave (producto_id)=(90) no está presente en la tabla «productos».inserción o actualización en la tabla «detalle_pedido» viola la llave foránea «detalle_pedido_producto_id_fkey» 

ERROR:  inserción o actualización en la tabla «detalle_pedido» viola la llave foránea «detalle_pedido_producto_id_fkey»
SQL state: 23503
Detail: La llave (producto_id)=(90) no está presente en la tabla «productos».
```
EXITO. LA ULTIMA PRUEBA. quiero agregar un detalle_pedido de un pedido que existe y un producto que existe, pero que pide una cantidad mayor a la que esta presente en el sistema. En mi caso el producto 1 tiene 13 stock, asi que si pedimos mas que eso deberia de dar error:
```sql
INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (1, 1, 16, 280000);
```
Esto deberia de dar error:
```sql
ERROR:  ERROR, el stock del producto no es suficiente para el registro del detalle del pedido
CONTEXT:  función PL/pgSQL descontar_stock_producto() en la línea 8 en RAISE 

SQL state: P0001
```
EXITOOOO. algo de lo que me estoy dando cuenta es que la persona que agregue detalles, tiene toda la libertad de poner el precio unitario que tiene el detalle, ignorando el precio que tiene el producto. A lo mejor tendre que hacer otro trigger para arreglar esto? no me agrada la idea de que una persona tenga que andar viendo a cada rato el valor original del producto en la tabla de productos para agregarlo al precio unitario del detalle_producto con la buena intencion de mantener el orden en la base de datos

Para arreglar los contadores se pueden utilizar codigos asi:
```sql
SELECT setval('detalle_pedido_detalle_id_seq', (SELECT MAX(detalle_id) FROM detalle_pedido));
```
**Prueba numero 3: Se generan envios por cambio de estado (Trigger C)**
Para esto vamos a utilizar el Procedure G para cambiar el estado de algun pedido que este en pendiente y pase a estar procesado. Lo mas probable es que el contador este malardo y vuelva a ocurrir el mismo error en la prueba 2, pero no se sabe nada si lo intentamos.
```sql
CALL actualizar_estado_pedido(1,'procesado',8);
```
El pedido 1 tiene como estado pendiente, asi que es el caso perfecto para usarlo. Deberia funcionar todo bien xd:
```sql
ERROR:  Ya existe la llave (envio_id)=(1).llave duplicada viola restricción de unicidad «envios_pkey» 

ERROR:  llave duplicada viola restricción de unicidad «envios_pkey»
SQL state: 23505
Detail: Ya existe la llave (envio_id)=(1).
Context: sentencia SQL: «INSERT INTO envios(pedido_id, distribuidor_id, estado_envio, fecha_envio, tracking)
		VALUES (NEW.pedido_id, id_repartidor, 'enviando', CURRENT_DATE, codigo_tracking)»
función PL/pgSQL registrar_inicio_de_proceso_envio() en la línea 20 en sentencia SQL
sentencia SQL: «UPDATE pedidos SET estado = nuevo_estado WHERE pedido_id = id_pedido»
función PL/pgSQL actualizar_estado_pedido(integer,character varying,integer) en la línea 20 en sentencia SQL
```
En efecto, ocurre lo mismo que en la segunda prueba, asi que hay que agregar una instruccion inicial de que luego de cargar los procedures, triggers, funciones y tablas de la base de datos, hay usar consultas para volver a sincronizar los contadores para las primary keys:
```sql
SELECT setval('envios_envio_id_seq', (SELECT MAX(envio_id) FROM envios));
```
Ya, ahora si, no deberia dar problema. Y como resultado tenemos un:
```sql
CALL
```
EXITAZOOOOOOOOOOOOOOOOOOOOOOOOOOOO. Pero bueno ahora vienen las pruebas mas pajeras y posiblemente mas adelante le tenga que hacer unos cambios al codigo de los tracking porque no encajan los que cree a mano con los que se crean mediante el trigger... que pasaria si cambio el estado a un pedido que ya tenia el estado procesado
```sql
CALL actualizar_estado_pedido(1,'procesado',8);
```
Y como resultado nos da:
```sql
CALL
```
Mish, no se nos añadio nada a auditoria_pedidos ni a envios.....LO CUAL ERA LO ESPERADO WUAJAJAJA EXITAZOOOOOOO
**Prueba Numero 4: El trigger de notificacion de cambio de pedido funciona**
Para esto usaremos el procedure extra que hicimos:
```sql
CALL actualizar_estado_pedido(1,'pendiente',8);
```
Y como resultado nos da:
```sql
NOTICE:  Cliente Numero 38, Su Pedido 1 ha cambiado de estado a: pendiente
CALL
```
EXITOOOOOOO, ya vimos que funciona :D. ahora probemos el otro trigger que deberia salir si hacemos lo siguiente:
```sql
UPDATE envios 
SET estado_envio = 'enviando' 
WHERE pedido_id = 5;
```
El envio con pedido_id = 5 tiene como estado 'entregado'...y como resultado tenemos:
```sql
NOTICE:  Cliente Numero 24, su pedido 5 ha cambiado el estado de su envio a: enviando
UPDATE 1

Query returned successfully in 148 msec.
```
y el cliente asociado al pedido 5 es.... 24, lo cual significa que fue un EXITAZOOOO
**Prueba Numero 5: Verificar que no se pueden eliminar clientes con pedidos activos (Trigger E)**

Yap, se supone que si intentamos eliminar un cliente con pedidos activos no deberia dejarnos... asi que si realizamos la siguiente accion:
```sql
DELETE FROM clientes WHERE cliente_id = 38;
```
No se deberia eliminar el cliente puesto que tiene al menos un pedido que tiene como estado 'pendiente'. Por ende, esta accion deberia tirar un error:
```sql
ERROR:  ERROR, el cliente no se puede eliminar dado a que tiene pedidos activos
CONTEXT:  función PL/pgSQL verificar_eliminacion_cliente() en la línea 7 en RAISE 

SQL state: P0001
```
EXITO, pero que pasa si eliminamos a uno que en definitiva no tiene ningun pedido activo?:
```sql
DELETE FROM clientes WHERE cliente_id = 50;
```
Esto deberia de borrar el ultimo cliente, el cual no tiene ningun pedido enlazado a el. El resultado es el siguiente:
```sql
NOTICE:  Se ha eliminado el usuario
DELETE 1

Query returned successfully in 126 msec.
```
Y podemos ver que en efecto, El cliente numero 50 ha sido eliminado, lo cual es un EXITO
**Prueba numero 6: Verificar asignacion de pedidos a personal existente y correcto (Trigger F)**

Primero vamos a verificar si se puede agregar un pedido a un cliente que NO EXISTE:
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id) 
VALUES (99, 'pendiente', 5);
```
nos deberia de dar como resultado un error (En nuestro sistema solo hay 50 clientes):
```sql
ERROR:  Ya existe la llave (pedido_id)=(1).llave duplicada viola restricción de unicidad «pedidos_pkey» 

ERROR:  llave duplicada viola restricción de unicidad «pedidos_pkey»
SQL state: 23505
Detail: Ya existe la llave (pedido_id)=(1).
```
Verdad que hay que sincronizar los contadores de los PK:
```sql
SELECT setval('pedidos_pedido_id_seq', (SELECT MAX(pedido_id) FROM pedidos));
```
Ya con esto arreglado nos sale como resultado:
```sql
ERROR:  La llave (cliente_id)=(99) no está presente en la tabla «clientes».inserción o actualización en la tabla «pedidos» viola la llave foránea «pedidos_cliente_id_fkey» 

ERROR:  inserción o actualización en la tabla «pedidos» viola la llave foránea «pedidos_cliente_id_fkey»
SQL state: 23503
Detail: La llave (cliente_id)=(99) no está presente en la tabla «clientes».
```
Bien, ahora suponiendo que pasara lo mismo con un personal que no existe, probemos si se puede agregar con un personal que esta inactivo. Nuestra lista por ahora esta llena de personal que esta activo, asi que cambiemos eso:
```sql
UPDATE personal
SET activo = FALSE
WHERE personal_id = 2;
```
Esto deberia hacer que el personal 2 que es vendedor, se encuentre inactivo, y por ende no deberia dejar registrar el pedido con un vendedor inactivo. Usaremos la siguiente consulta
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id) 
VALUES (1, 'pendiente', 2);
```
y tenemos como resultado:
```sql
ERROR:  ERROR, el personal asignado no esta activo
CONTEXT:  función PL/pgSQL verificar_asignacion_pedido() en la línea 9 en RAISE 

SQL state: P0001
```
Exito. Ahora devolvamosle la actividad al personal
```sql
UPDATE personal
SET activo = TRUE
WHERE personal_id = 2;
```
Y probemos que pasa si usamos a alguien del personal que NO SEA VENDEDOR
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id) 
VALUES (2, 'pendiente', 1);
```
Nos deberia dar error. El resulado es:
```sql
ERROR:  ERROR, el personal asignado no es un vendedor, DEBE SERLO
CONTEXT:  función PL/pgSQL verificar_asignacion_pedido() en la línea 14 en RAISE 

SQL state: P0001
```
BIEN, ahora verifiquemos si esto permite insertar un pedido por parte de un vendedor activo
```sql
INSERT INTO pedidos (cliente_id, estado, vendedor_id) 
VALUES (2, 'pendiente', 2);
```
Como resultado nos salio INSERT 0 1 y podemos ver en la tabla de pedidos que en efecto, todo salio como esperaba (Mucho cuidado con las mayusculas por cierto xd)

**Prueba numero 7: Verificar mensaje de stock critico (Trigger G)**

Verifiquemos si sale el mensaje o no
```sql
UPDATE productos SET stock = 3 WHERE producto_id = 5;
```
El resultado es:
```sql
NOTICE:  El stock del producto 5 recientemente usado presenta un stock CRITICO: 3 unidades restantes
UPDATE 1

Query returned successfully in 126 msec.
```
Funciona


**Prueba numero 8: Registrar pago de un pedido pendiente (Procedimiento B)**
Vamos a intentar pagar un pedido que no existe
```sql
CALL registrar_pago(99, 5000, 'tarjeta');
```
Esto deberia de dar error. El resultado que nos salio es:
```sql
ERROR:  ERROR, el pedido que quieres pagar no presenta un costo o no existe en nuestra base de datos
CONTEXT:  función PL/pgSQL registrar_pago(integer,integer,character varying) en la línea 9 en RAISE 

SQL state: P0001
```
Bien, ahora intentemos pagar un pedido que exista pero no este pendiente
```sql
CALL registrar_pago(3,589980,'tarjeta');
```
Deberia salir una de las exceptions. El resultado es:
```sql
ERROR:  ERROR, este pedido no presenta el estado pendiente, por ende, el pago ya fue realizado para este pedido
CONTEXT:  función PL/pgSQL registrar_pago(integer,integer,character varying) en la línea 15 en RAISE 

SQL state: P0001
```
Bien, ahora intentemos pagar un pedido que exista y que este pendiente pero con un monto insuficiente
```sql
CALL registrar_pago(1,1000,'tarjeta');
```
Deberia salir otra exception. El resultado es:
```sql
ERROR:  ERROR, el monto otorgado es menor a lo que hay que pagar
CONTEXT:  función PL/pgSQL registrar_pago(integer,integer,character varying) en la línea 19 en RAISE 

SQL state: P0001
```
Bien, ahora intentemos pagar un pedido que exista y que este pendiente y con un monto igual o superior, pero con un metodo de pago no permitido por nuestra base de datos
```sql
CALL registrar_pago(1,779970,'francodolares');
```
Deberia salir otra exception. El resultado es:
```sql
ERROR:  ERROR, la forma de pago no es aceptada en nuestra base de datos (se recomienda solo uso de minusculas para declarar tu tipo de pago)
CONTEXT:  función PL/pgSQL registrar_pago(integer,integer,character varying) en la línea 24 en RAISE 

SQL state: P0001
```
Bien, ahora intentemos pagar un pedido que exista y que este pendiente y con un monto igual o superior y con un metodo de pago admitido por nuestra base de datos
```sql
CALL registrar_pago(1,779970,'efectivo');
```
Deberia salir todo bien. Eso si creo que antes de realizar esto debemos sincronizar el contador de serial de pagos:
```sql
SELECT setval('pago_pago_id_seq', (SELECT MAX(pago_id) FROM pago));
```
Una vez hecho esto, nuestro resultado es:
```sql
NOTICE:  Cliente Numero 38, Su Pedido 1 ha cambiado de estado a: procesado
NOTICE:  Pago registrado
CALL

Query returned successfully in 144 msec.
```
EXITOOOOO, y si revisamos la tabla de pagos, podemos ver que si se registro

**Prueba Numero 9: Verificar impresion correcta de tabla de ganancias mensuales de vendedores**
Usamos esta consulta:
```sql
SELECT * FROM generar_reporte_ventas(6, 2025);
```
y nos genera las listas deseadas... xd nose como colocar la tabla aca sjkdnskjdnskjd

**Prueba Numero 10: Verificar impresion correcta de tabla de entregas realizadas por cada distribuidor**
Usamos esta consulta:
```sql
SELECT * FROM generar_informe_entregas_distribuidor();
```
y nos genera la lista deseada :D

**Prueba Numero 11: Verificar cambio de umbral critico por producto**
Vamos a cambiar el valor del umbral critico de un producto con la siguiente consulta:
```sql
CALL actualizar_umbral_critico(12, 6);
```
Esto deberia de cambiar el producto 12 a tener el valor de umbral critico de 4 a 6. Vamos a ver:
```sql
NOTICE:  Umbral critico editado
CALL
````
EXITO

**Prueba Numero 12: Verificar envio de notificaciones a usuarios respecto a los cambios de estado de sus pedidos**
Usamos esta consulta:
```sql
CALL notificar_actualizacion_de_estado_cliente(38);
```
El cliente 38 (al menos en mi base de datos) es el unico que presenta datos de cambio de estado en auditoria_pedidos (probamos en una prueba anterior con el pedido numero 1). Por ende si le deberia informar acerca de los cambios realizados en sus pedidos. Como resultado tenemos que:

```sql
NOTICE:  Pamela Maria, Tu pedido con id 1 Tuvo un cambio de estado: de pendiente a procesado
CALL

Query returned successfully in 103 msec
```
EXITO. Que pasa si pedimos la id de alguien que no existe?:
```sql
ERROR: la id ingresada no esta presente en nuestra base de datos
CONTEXT:  función PL/pgSQL notificar_actualizacion_de_estado_cliente(integer) en la línea 9 en RAISEERROR:  ERROR: la id ingresada no esta presente en nuestra base de datos
SQL state: P0001
```
Perfecto
