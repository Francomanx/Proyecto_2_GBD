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

#metodo para generar pedidos
def generar_pedido(num_pedidos, id_clientes, id_vendedores):
    id_counter = 1
    pedidos = []

    #generamos pedidos
    for _ in range(num_pedidos):
        cliente_id = random.choice(id_clientes)
        fecha_pedido = fake.date_this_month()
        estado = random.choice(['pendiente','procesado','entregado']) #tambien existe la posibilidad de que un pedido este cancelado creo, pero por ahora mejor dejemoslo asi
        total = random.randint(29990,499990) #Estos valores son obsoletos pero una vez que se realicen los triggers para calcular los montos reales, tendran los valores correctos
        vendedor_id = random.choice(id_vendedores)
        pedidos.append([id_counter, cliente_id, fecha_pedido, estado, total, vendedor_id])
        id_counter += 1
    return pedidos

id_clientes = []

with open('clientes_data.csv', newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        id_clientes.append(row['cliente_id'])

id_vendedores = []

with open('personal_data.csv', newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        if row['rol']=='Vendedor':
            id_vendedores.append(row['personal_id'])

#Generamos 15 pedidos
pedido_data = generar_pedido (15, id_clientes, id_vendedores)

#y los guardamos en un archivo.csv
with open('pedido_data.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["pedido_id", "cliente_id", "fecha_pedido", "estado", "total", "vendedor_id"])
    writer.writerows(pedido_data)          
print("Datos de pedidos generados correctamente.")
