from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from celery import Celery

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'recetas_flask@gmail.com'
app.config['MAIL_PASSWORD'] = 'celary2004'  

mail = Mail(app)


app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recetas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Receta(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    ingredientes = db.Column(db.Text, nullable=False)
    pasos = db.Column(db.Text, nullable=False)

def iniciar_db():
    with app.app_context():
        db.create_all()

@celery.task
def enviar_correo_asincrono(asunto, destinatarios, cuerpo):
    with app.app_context():
        msg = Message(asunto, sender=app.config['MAIL_USERNAME'], recipients=destinatarios)
        msg.body = cuerpo
        mail.send(msg)

@app.route('/enviar-correo', methods=['POST'])
def enviar_correo():
    if request.method == 'POST':
        email = request.form['email']
        asunto = "Recetario - Nueva receta agregada"
        cuerpo = "Se ha añadido una nueva receta a nuestro recetario. ¡Revisa la página!"
        
        
        enviar_correo_asincrono.delay(asunto, [email], cuerpo)
        flash('Correo en proceso de envío.', 'success')
        return redirect(url_for('home'))


@app.route('/agregar', methods=['GET', 'POST'])
def agregar_receta():
    if request.method == 'POST':
        nombre = request.form['nombre']
        ingredientes = request.form['ingredientes']
        pasos = request.form['pasos']

        if not nombre or not ingredientes or not pasos:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('agregar_receta'))

        nueva_receta = Receta(nombre=nombre, ingredientes=ingredientes, pasos=pasos)
        db.session.add(nueva_receta)
        db.session.commit()

        # Enviar correo notificando la nueva receta
        enviar_correo_asincrono.delay(
            "Nueva receta agregada",
            ["listarecetas@gmail.com"],  # Cambia esto a tu correo o lista de correos
            f"Se ha añadido una nueva receta: {nombre}"
        )

        flash('Receta agregada exitosamente y correo enviado.', 'success')
        return redirect(url_for('home'))

    return render_template('agregar.html')

if __name__ == "__main__":
    iniciar_db()
    app.run(debug=True)
