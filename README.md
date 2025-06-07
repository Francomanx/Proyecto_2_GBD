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
