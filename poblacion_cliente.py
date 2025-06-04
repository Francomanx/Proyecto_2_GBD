from faker import Faker
import random
import csv
import unicodedata
fake = Faker('es_CL')  #con esto practicamente los valores van a ser en su mayoria chilenos (nombres, direcciones, etc)

#metodo para generar un rut
def generar_rut():
    rut = random.randint(10000000, 99999999)
    dv = random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'K'])
    return f"{rut}-{dv}"

# Método para limpar texto.
def limpiar_texto(texto):
    if isinstance(texto, str):
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto

#metodo para generar datos de clientes
def generar_cliente(num_clientes):
    id_counter = 1
    clientes = []
    ruts = []
    emails = []

    #generamos clientes
    for _ in range(num_clientes):
        nombre = limpiar_texto(fake.first_name() + " " + fake.first_name()) #no hay necesidad de asegurarse de que los nombres aparezcn mas de dos veces
        correo_electronico = limpiar_texto(fake.email())
        #los correos electronicos son unicos
        while correo_electronico in emails:
            correo_electronico = limpiar_texto(fake.email())
        telefono = "+569" + str(random.randint(10000000, 99999999))
        direccion = limpiar_texto(fake.street_name()[:50]) #esta vez no hay limites en los caracteres de las direcciones pero igual es mejor tener una direccion corta
        fecha_nacimiento = fake.date_of_birth(minimum_age=18, maximum_age=80) #con esto nos aseguramos de que si o si el usuario registrado tenga al menos 18 añitos
        rut = generar_rut()
        #los ruts son unicos
        while rut in ruts:
            rut = generar_rut()
        fecha_registro = fake.date_this_decade() #todos los registros seran realizados en un lapso de una decada (2015 a 2025)

        clientes.append([id_counter, nombre, correo_electronico, telefono, direccion, fecha_nacimiento, rut, fecha_registro])
        emails.append(correo_electronico)
        ruts.append(ruts)
        id_counter += 1
    
    return clientes

#Generamos 50 clientes
clientes_data = generar_cliente(50)

#y los guardamos en un archivo.csv
with open('clientes_data.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["cliente_id", "nombre", "correo_electronico", "telefono", "direccion", "fecha_nacimiento", "rut", "fecha_registro"])
    writer.writerows(clientes_data)          
print("Datos de clientes generados correctamente.")