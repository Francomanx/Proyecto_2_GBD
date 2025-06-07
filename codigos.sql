-- Active: 1749310796709@@127.0.0.1@5432@proyecto2gestion

CREATE OR REPLACE VIEW Resumen_Pedidos_Clientes AS
SELECT 
    p.pedido_id,
    c.nombre AS nombre_cliente,
    c.rut,
    p.fecha_pedido,
    p.total,
    p.estado
FROM pedidos p
JOIN clientes c ON p.cliente_id = c.cliente_id;


drop view if exists Historial_Cliente;

SELECT * FROM Historial_Cliente;

