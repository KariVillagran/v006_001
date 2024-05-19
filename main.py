from flask import Flask
from flask import render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import Security
import requests
import random
import string

main=Flask(__name__)
main.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root@localhost/ferremas'
main.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

db = SQLAlchemy(main)
ma = Marshmallow(main)

CORS(main)

cors = CORS(main, resource={
    r"/api/v1/transbank/*":{
        "origins" : "*"
    }
})

########################################################################################################################################
def generate_random_string(length=10):
    """Genera una cadena aleatoria de caracteres alfanuméricos."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def header_request_transbank():
    headers = {
        "Content-Type" : "application/json;charset=UTF-8",
        "Tbk-Api-Key-Id" : "597055555532",
        "Tbk-Api-Key-Secret" : "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C",
        "Access-Control-Allow-Origin" : "*",
    }
    return headers

def body_transbank(total):
    # Genera códigos aleatorios para buy_order y session_id
    buy_order = generate_random_string(10)  # Genera una cadena aleatoria de longitud 10
    session_id = generate_random_string(12)  # Genera una cadena aleatoria de longitud 12
    
    body = {
        "buy_order": buy_order,
        "session_id": session_id,    
        "amount": total,
        "return_url": "http://www.comercio.cl/webpay/retorno",
    }
    return body

@main.route('/api/v1/transbank/transaction/create',methods=['POST'])
def transbank_create():
    data = request.json
    print('data', data)
    url = 'https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions'
    headers = header_request_transbank()
    response = requests.post(url,json=data, headers=headers)

    token = response.json()["token"]
    urlresponse = response.json()["url"]

    output = urlresponse+'?token_ws='+token

    return jsonify({"response URL":output}), 200

@main.route('/api/v1/transbank/<int:codigo_cliente>/comprar', methods=['POST'])
def comprar(codigo_cliente):

    #Calcular el total

    productos_en_carrito = Carritos.query.filter_by(codigo_usuario=codigo_cliente).all()
    if not productos_en_carrito:
        return jsonify({"mensaje": "El carrito está vacío"}), 404

    total = 0

    productos = []
    for item in productos_en_carrito:
        producto = Productos.query.get(item.codigo_producto)
        productos.append({"id": producto.codigo_producto, "nombre": producto.nombre, "precio": producto.precio})
        total = producto.precio + total

    data = body_transbank(total)
    url = 'https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions'
    headers = header_request_transbank()
    response = requests.post(url,json=data, headers=headers)

    token = response.json()["token"]
    urlresponse = response.json()["url"]

    output = urlresponse+'?token_ws='+token

    return jsonify({"response URL":output}), 200

@main.route('/api/v1/transbank/transaction/commit/<string:tokenws>', methods=['PUT'])
def transbank_commit(tokenws):
    print('tokenws: ', tokenws)
    
    url = "https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions/{0}".format(tokenws)
    
    headers = header_request_transbank()
       
    response = requests.put(url, headers=headers)
    print('response: ', response.json())
    
    req_Json = response.json()

    monto = req_Json['amount']
    status = req_Json['status']
    fecha = req_Json['transaction_date']
    buy_order = req_Json['buy_order']
    session_id = req_Json['session_id']
        
    new_insert = Ventas(monto,status,fecha,buy_order,session_id)
    db.session.add(new_insert)
    db.session.commit()

    return jsonify(response.json()), 200


########################################################################################################################################

class Clientes(db.Model):
    codigo_cliente = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(70),unique=True)
    password = db.Column(db.String(70))
    email = db.Column(db.String(70))

    def __init__(self, user, password, email):
        self.user = user
        self.password = password
        self.email = email

class Usuarios(db.Model):
    codigo_usuario = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(70),unique=True)
    password = db.Column(db.String(70))
    rol = db.Column(db.String(70))

    def __init__(self, user, password, rol):
        self.user = user
        self.password = password
        self.rol = rol

class Productos(db.Model):
    codigo_producto = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(70))
    codigo = db.Column(db.String(70))
    nombre = db.Column(db.String(70))
    precio = db.Column(db.Integer)
    fecha = db.Column(db.String(70))
    stock = db.Column(db.Integer)

    def __init__(self, marca, codigo, nombre, precio, fecha, stock):
        self.marca = marca
        self.codigo = codigo
        self.nombre = nombre
        self.precio = precio
        self.fecha = fecha
        self.stock = stock

class Roles(db.Model):
    codigo_rol = db.Column(db.Integer, primary_key=True)
    rol = db.Column(db.String(70),unique=True)

    def __init__(self,rol):
        self.rol = rol

class Carritos(db.Model):
    codigo_carrito = db.Column(db.Integer, primary_key=True)
    codigo_producto = db.Column(db.Integer)
    codigo_usuario = db.Column(db.Integer)

    def __init__(self,codigo_producto,codigo_usuario):
        self.codigo_producto = codigo_producto
        self.codigo_usuario =  codigo_usuario

class Ventas(db.Model):
    codigo_venta = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Integer)
    status = db.Column(db.String(70))
    fecha = db.Column(db.String(70))
    buy_order = db.Column(db.String(70))
    session_id = db.Column(db.String(70))

    def __init__(self, monto, status, fecha,buy_order,session_id):
        self.monto = monto
        self.status = status
        self.fecha = fecha
        self.buy_order = buy_order
        self.session_id = session_id

with main.app_context():
    db.create_all()

class VentasSchema(ma.Schema):
    class Meta:
        fields = ('codigo_venta','monto','status','fecha','buy_order','session_id')

task5_schema = VentasSchema()
tasks5_schema = VentasSchema(many=True)

class ProductosSchema(ma.Schema):
    class Meta:
        fields = ('codigo_producto','marca','codigo','nombre','precio','fecha','stock')

task_schema = ProductosSchema()
tasks_schema = ProductosSchema(many=True)

class UsuariosSchema(ma.Schema):
    class Meta:
        fields = ('codigo_usuario','user','password','rol')

task1_schema = UsuariosSchema()
task1s_schema = UsuariosSchema(many=True)

class RolSchema(ma.Schema):
    class Meta:
        fields = ('codigo_rol','rol')

task2_schema = RolSchema()
task2s_schema = RolSchema(many=True)

class CarritoSchema(ma.Schema):
    class Meta:
        fields = ('codigo_carrito','codigo_producto','codigo_usuario')

task3_schema = CarritoSchema()
task3s_schema = CarritoSchema(many=True)

class ClientesSchema(ma.Schema):
   class Meta:
        fields = ('codigo_cliente','user','password','email') 

task4_schema = ClientesSchema()
task4s_schema = ClientesSchema(many=True)

########################################################################################################################################

@main.route('/')
def inicio():
    return render_template('sitio/index.html')

@main.route('/materiales_basicos')
def materiales_basicos():
    return render_template('sitio/materiales_basicos.html')

@main.route('/contacto')
def contacto():
    return render_template('sitio/contacto.html')

@main.route('/insertar_productos',methods=['POST'])
def insertar_productos():
    ##rescatar datos para tabla_productos
    token_vy = Security.Security.validar_token(request.headers)
    if token_vy:
        req_Json = request.json

        marca = req_Json['marca']
        codigo = req_Json['codigo']
        nombre = req_Json['nombre']
        precio = req_Json['precio']
        fecha = req_Json['fecha']
        stock = req_Json['stock']
        
        new_insert = Productos(marca,codigo,nombre,precio,fecha,stock)
        db.session.add(new_insert)
        db.session.commit()

        return task_schema.jsonify(new_insert)
    else:
        return jsonify({'message':'Unauthorized'})

@main.route('/consultar_productos',methods=['GET'])
def consultar_productos():
    
     all_productos = Productos.query.all()
     result = tasks_schema.dump(all_productos)
     return jsonify(result)
    

@main.route('/consultar_produto/<codigo_producto>',methods=['GET'])
def consultar_producto(codigo_producto):
    
        producto = Productos.query.get(codigo_producto)
        return task_schema.jsonify(producto)


@main.route('/insertar_usuario',methods=['POST'])
def insertar_usuario():
    token_vy = Security.Security.validar_token(request.headers)
    if token_vy:
    ##rescatar datos para tabla_productos
        req_Json = request.json

        user = req_Json['user']
        password = req_Json['password']
        rol = req_Json['rol']

        new_insert = Usuarios(user,password,rol)
        db.session.add(new_insert)
        db.session.commit()

        return task1_schema.jsonify(new_insert)
    else:
        return jsonify({'message':'Unauthorized'})

@main.route('/login',methods=['POST'])
def login():
    req_Json = request.json
    
    username = req_Json['user']
    password = req_Json['password']

    user_authenticated = Usuarios.query.filter(Usuarios.user == username, Usuarios.password == password).all()

    user1 = None
    pass1 = None
    rol1 = None

    for users in user_authenticated:
        user1 = users.user
        pass1 = users.password
        rol1  = users.rol
        break

    if (user1 != None):
        encode_token = Security.Security.generate_Token(user1,pass1,rol1)
        return jsonify({'success':True, 'token': encode_token})
    else:
        return jsonify({'success':False})

@main.route('/insertar_roles',methods=['POST'])
def insertar_roles():
    token_vy = Security.Security.validar_token(request.headers)
    if token_vy:
    ##rescatar datos para tabla_productos
        req_Json = request.json

        rol = req_Json['rol']

        new_insert = Roles(rol)
        db.session.add(new_insert)
        db.session.commit()

        return task2_schema.jsonify(new_insert)
    else:
        return jsonify({'message':'Unauthorized'})

@main.route('/registrar_cliente',methods=['POST'])
def registrar_cliente():
    ##rescatar datos para tabla_productos
    req_Json = request.json

    user = req_Json['user']
    password = req_Json['password']
    email = req_Json['email']
    
    new_insert = Clientes(user,password,email)
    db.session.add(new_insert)
    db.session.commit()

    return task4_schema.jsonify(new_insert)

@main.route('/carrito/<int:codigo_cliente>/agregar/<int:codigo_producto>',methods=['POST'])
def agregar_carrito(codigo_cliente,codigo_producto):
    producto = Productos.query.get(codigo_producto)

    cliente = Clientes.query.get(codigo_cliente)

    if not cliente:
        return jsonify({'mensaje':'Cliente no encontrado'}), 404
    if not producto:
        return jsonify({'mensaje':'Producto no encontrado'}), 404

    print(codigo_producto,codigo_cliente)

    count_carro = Carritos.query.filter_by(codigo_usuario=codigo_cliente).count()

    print(count_carro)

    if count_carro < 7:
        nuevo_prod = Carritos(codigo_producto,codigo_cliente)
        db.session.add(nuevo_prod)
        db.session.commit()
        return task3_schema.jsonify(nuevo_prod)
    else:
        return jsonify({'mensaje':'Carro lleno'}), 404

@main.route('/carrito/<int:codigo_cliente>/eliminar/<int:codigo_producto>', methods=['DELETE'])
def eliminar_del_carrito(codigo_cliente, codigo_producto):
    item = Carritos.query.filter_by(codigo_usuario=codigo_cliente, codigo_producto=codigo_producto).first()
    if not item:
        return jsonify({"mensaje": "Producto no encontrado en el carrito"}), 404
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({"mensaje": "Producto eliminado del carrito"}), 200

@main.route('/carrito/<int:codigo_cliente>', methods=['GET'])
def ver_carrito(codigo_cliente):
    productos_en_carrito = Carritos.query.filter_by(codigo_usuario=codigo_cliente).all()
    if not productos_en_carrito:
        return jsonify({"mensaje": "El carrito está vacío"}), 404  
    
    productos = []
    for item in productos_en_carrito:
        producto = Productos.query.get(item.codigo_producto)
        productos.append({"id": producto.codigo_producto, "nombre": producto.nombre, "precio": producto.precio})
    
    return jsonify(productos)


@main.route('/consultar_ventas',methods=['GET'])
def consultar_ventas():
    token_vy = Security.Security.validar_token(request.headers)
    if token_vy:
        all_ventas = Ventas.query.all()
        print(all_ventas)
        result = tasks5_schema.dump(all_ventas)
        print(result)
        return jsonify(result)
    else:
        return jsonify({'message':'Unauthorized'})


if __name__ == '__main__':
    main.run(debug=True)
