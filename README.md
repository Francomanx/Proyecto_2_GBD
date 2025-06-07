## Proyecto_2_GBD
no hace nada

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
CONSTRAINT precio_valido CHECK (precio>=0)
);
```
```sql
CREATE TABLE personal(
personal_id SERIAL PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
rol VARCHAR (50) NOT NULL,
correo VARCHAR(100) UNIQUE NOT NULL,
telefono VARCHAR(20)
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
consideremos hacer uno para actualizar el precio unitario de los productos en detalle_pedido. La idea que tengo es que el precio unitario de detalle_pedido deberia tener el mismo valor que presenta al producto que referencia a traves de producto_id. En el faker es facil de hacer pero nose como referenciarlo a traves de sql, asi que creo que toco hacer un trigger adicional pipipi

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
