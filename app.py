from flask import Flask, render_template, request, redirect, url_for, flash
from models import Propietario, Vehiculo, Parqueo, Facturacion

app = Flask(__name__)
app.secret_key = 'una_clave_secreta_muy_segura_y_unica_para_produccion' 


parqueo_manager = Parqueo(filas=4, columnas=5)
facturacion_manager = Facturacion()

@app.route('/')
def dashboard():
    """Muestra el panel principal del sistema de parqueo."""
    
    parqueo_manager.actualizar_estado_desde_db()
    estado_parqueo = parqueo_manager.mapa
    lista_espera = parqueo_manager.lista_espera
    return render_template('dashboard.html', estado_parqueo=estado_parqueo, lista_espera=lista_espera)

@app.route('/registrar-propietario', methods=['GET', 'POST'])
def registrar_propietario():
    if request.method == 'POST':
        try:
            Propietario.agregar(
                cedula=request.form['cedula'],
                nombre=request.form['nombre'],
                telefono=request.form['telefono'],
                direccion=request.form['direccion']
            )
            flash('Propietario registrado con éxito!', 'success')
        except Exception as e:
            flash(f'Error al registrar propietario: La cédula ya podría existir. ({e})', 'danger')
        return redirect(url_for('registrar_propietario'))
    return render_template('registrar_propietario.html')

@app.route('/registrar-vehiculo', methods=['GET', 'POST'])
def registrar_vehiculo():
    if request.method == 'POST':
        try:
            Vehiculo.agregar(
                placa=request.form['placa'].upper(),
                marca=request.form['marca'],
                modelo=request.form['modelo'],
                propietario_cedula=request.form['propietario_cedula']
            )
            flash('Vehículo registrado con éxito!', 'success')
        except Exception as e:
            flash(f'Error al registrar vehículo: La placa ya podría existir. ({e})', 'danger')
        return redirect(url_for('registrar_vehiculo'))
    
    propietarios = Propietario.todos()
    return render_template('registrar_vehiculo.html', propietarios=propietarios)

@app.route('/ingresar', methods=['POST'])
def ingresar_vehiculo():
    placa = request.form['placa'].upper()
    mensaje = parqueo_manager.registrar_entrada(placa)
    if "Error" in mensaje:
        flash(mensaje, 'danger')
    else:
        flash(mensaje, 'info')
    return redirect(url_for('dashboard'))

@app.route('/retirar', methods=['POST'])
def retirar_vehiculo():
    """
    Procesa la salida, genera una factura y redirige a la vista de la factura.
    """
    placa = request.form['placa'].upper()
    mensaje_salida = parqueo_manager.registrar_salida(placa)
    
    if "Error" in mensaje_salida:
        flash(mensaje_salida, 'danger')
        return redirect(url_for('dashboard'))
    
    try:
       
        factura_id = facturacion_manager.generar_factura(placa)
        flash(mensaje_salida, 'success')
        
        return redirect(url_for('ver_factura', factura_id=factura_id))
    except Exception as e:
        flash(f'Error al generar la factura: {e}', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/factura/<int:factura_id>')
def ver_factura(factura_id):
    """
    Muestra los detalles de una factura específica.
    """
    factura = Facturacion.obtener_factura(factura_id)
    if not factura:
        flash('Error: Factura no encontrada.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('factura.html', factura=factura)


if __name__ == '__main__':
    app.run(debug=True, port=5001)