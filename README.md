# Proyecto_2_GBD
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

## Procedures (Funciones)

## Triggers
consideremos hacer uno para actualizar el precio unitario de los productos en detalle_pedido. La idea que tengo es que el precio unitario de detalle_pedido deberia tener el mismo valor que presenta al producto que referencia a traves de producto_id. En el faker es facil de hacer pero nose como referenciarlo a traves de sql, asi que creo que toco hacer un trigger adicional pipipi
