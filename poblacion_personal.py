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

#metodo para generar datos de personal
def generar_personal(num_personal, emails_clientes):
    id_counter = 1
    personals = []
    emails = []
    
    #generamos el personal
    for _ in range(num_personal):
        nombre = limpiar_texto(fake.first_name() + " " + fake.first_name())
        rol = random.choice(['Vendedor','Distribuidor','Administrador'])
        correo = limpiar_texto(fake.email())
        #supongo que hay que tratarlo igual que los otros correos
        while correo in emails or correo in emails_clientes:
            correo = limpiar_texto(fake.email())
        telefono = "+569" + str(random.randint(10000000, 99999999))

        personals.append([id_counter, nombre, rol, correo, telefono])
        id_counter += 1
        emails.append(correo)

    return personals

emails_clientes = []

with open('clientes_data.csv', newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        emails_clientes.append(row['correo_electronico'])

#Generamos 30 personales
personal_data = generar_personal(30, emails_clientes)

#y los guardamos en un archivo.csv
with open('personal_data.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["personal_id", "nombre", "rol", "correo", "telefono"])
    writer.writerows(personal_data)          
print("Datos de personal generados correctamente.")