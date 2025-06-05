from faker import Faker
import random
import csv
import unicodedata
fake = Faker('es_CL')  #con esto practicamente los valores van a ser en su mayoria chilenos (nombres, direcciones, etc)

# Método para limpar texto.
def limpiar_texto(texto):
    if isinstance(texto, str):
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto

#metodo para generar datos de detalles de pedido
def generar_detalles_pedido(num_detalles, id_productos, precio_productos):
    id_counter_detalle = 1
    id_counter_pedido = 1 #quiero intentar que hayan al menos dos tipos de productos por pedido
    detalles_pedidos = []

    #generamos los detalles
    for _ in range(num_detalles):
        #primer detalle
        pedido_id1 = id_counter_pedido
        producto_id1 = random.choice(id_productos)
        cantidad1 = random.randint(1,3) #de 1 a 3 productos comprados
        #para seleccionar el precio unitario, voy a recorrer la lista de precios de productos
        i = 0
        while i<len(id_productos):
            #si resulta encontrar el id en i posicion, significa que el precio de ese producto tambien esta en la i posicion de precio_productos
            if id_productos[i]==producto_id1:
                precio_unitario1 = precio_productos[i]
            i += 1
        
        #segundo detalle
        pedido_id2 = id_counter_pedido
        producto_id2 = random.choice(id_productos)
        #En este caso, para seguir las reglas acordadas por la tabla SQL
        #un pedido no puede tener productos duplicados, entonces:
        while producto_id1 == producto_id2:
            producto_id2 = random.choice(id_productos)
        cantidad2 = random.randint(1,3)
        #mismo proceso para seleccionar el precio
        j = 0
        while j<len(id_productos):
            #si resulta encontrar el id en i posicion, significa que el precio de ese producto tambien esta en la i posicion de precio_productos
            if id_productos[j]==producto_id2:
                precio_unitario2 = precio_productos[j]
            j += 1

        detalles_pedidos.append([id_counter_detalle,pedido_id1,producto_id1,cantidad1,precio_unitario1])
        id_counter_detalle += 1
        detalles_pedidos.append([id_counter_detalle,pedido_id2,producto_id2,cantidad2,precio_unitario2])
        id_counter_detalle += 1
        id_counter_pedido += 1
        #De esta forma habrian dos detalles pedido por pedido (e s p e r o)
    return detalles_pedidos

id_productos = []
precio_productos = []

with open('productos_data.csv', newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        id_productos.append(row['producto_id'])
        precio_productos.append(row['precio'])

#Como hay 15 pedidos y queremos generar 2 detalles por pedido, al pedir 15 saldran 30
detalles_pedido_data = generar_detalles_pedido(15, id_productos, precio_productos)

#y los guardamos en un archivo.csv
with open('detalles_pedido_data.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["detalle_id", "pedido_id", "producto_id", "cantidad", "precio_unitario"])
    writer.writerows(detalles_pedido_data)          
print("Datos de detalles de pedido generados correctamente.")