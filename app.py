from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import flash
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///supply_chain.db'
db = SQLAlchemy(app)
app.secret_key = 'a_random_string_that_is_hard_to_guess'

from flask_migrate import Migrate

migrate = Migrate(app, db)
# Database Models
class Manufacturer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(200))
    contact_info = db.Column(db.String(100))
    risk_rating = db.Column(db.Integer, nullable=False)
    occupation_rate = db.Column(db.Float, default=0)  # New column for workload occupation rate
    facing_blocks = db.Column(db.Boolean, default=False)  # New column to capture if the supplier is facing blocks
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))  # New ForeignKey column
    checkpoint = db.Column(db.Integer, default=0)  # New field for checkpoint number
    geopolitical_risks = db.relationship('GeopoliticalRisk', backref='supplier', lazy=True)



class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('manufacturer.id'), nullable=False)
    suppliers = db.relationship('Supplier', backref='project', lazy=True)
    scope1_emission = db.Column(db.Float, default=0)
    scope2_emission = db.Column(db.Float, default=0)
    scope3_emission = db.Column(db.Float, default=0)

class GeopoliticalRisk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)  # Description of the geopolitical risk
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)  # Linking the risk to a specific supplier
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Time when the risk was uploaded



@app.route('/')
def dashboard():
    manufacturers = Manufacturer.query.all()
    suppliers = Supplier.query.all()
    return render_template('dashboard.html', manufacturers=manufacturers, suppliers=suppliers)


@app.route('/add_manufacturer', methods=['GET', 'POST'])
def add_manufacturer():
    if request.method == 'POST':
        name = request.form['name']
        manufacturer = Manufacturer(name=name)
        db.session.add(manufacturer)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_manufacturer.html')


@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact_info = request.form['contact_info']
        risk_rating = request.form.get('risk_rating', type=int)

        if not name or not address or not contact_info or not risk_rating:
            error = "Please fill out all required fields."
        elif not (1 <= risk_rating <= 10):
            error = "Risk rating must be between 1 and 10."

        if not error:
            supplier = Supplier(name=name, address=address, contact_info=contact_info, risk_rating=risk_rating)
            db.session.add(supplier)
            db.session.commit()
            return redirect(url_for('dashboard'))

    return render_template('add_supplier.html', error=error)


@app.route('/edit_supplier/<int:id>', methods=['GET', 'POST'])
def edit_supplier(id):
    supplier = Supplier.query.get(id)
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.address = request.form['address']
        supplier.contact_info = request.form['contact_info']
        supplier.risk_rating = int(request.form['risk_rating'])
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_supplier.html', supplier=supplier)


@app.route('/delete_supplier/<int:id>', methods=['POST'])
def delete_supplier(id):
    supplier = Supplier.query.get(id)
    db.session.delete(supplier)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project_name = request.form['project_name']
        manufacturer_id = request.form['manufacturer_id']
        scope1_emission = float(request.form['scope1_emission'])
        scope2_emission = float(request.form['scope2_emission'])
        scope3_emission = float(request.form['scope3_emission'])

        # Validation for project_name, manufacturer_id, and emissions can be added here

        new_project = Project(name=project_name, manufacturer_id=manufacturer_id, scope1_emission=scope1_emission, scope2_emission=scope2_emission, scope3_emission=scope3_emission)
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('dashboard'))

    manufacturers = Manufacturer.query.all()
    return render_template('add_project.html', manufacturers=manufacturers)


@app.route('/view_project/<int:id>', methods=['GET'])
def view_project(id):
    project = Project.query.get_or_404(id)  # Get the project or return 404 if not found
    manufacturer = Manufacturer.query.get(project.manufacturer_id)
    suppliers = Supplier.query.filter_by(project_id=id).all()

    return render_template('view_project.html', project=project, manufacturer=manufacturer, suppliers=suppliers)


@app.route('/update_project/<int:id>', methods=['GET', 'POST'])
def update_project(id):
    project = Project.query.get_or_404(id)  # Get the project or return 404 if not found

    if request.method == 'POST':
        project.name = request.form['name']
        project.manufacturer_id = request.form['manufacturer_id']

        db.session.commit()  # Save changes to the database

        return redirect(url_for('view_project', id=id))  # Redirect to the project view page

    manufacturers = Manufacturer.query.all()  # To populate the dropdown in the form

    return render_template('update_project.html', project=project, manufacturers=manufacturers)

from flask import request, redirect, url_for

@app.route('/upload_esg/<int:project_id>', methods=['GET', 'POST'])
def upload_esg(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.scope1_emission = float(request.form['scope1'])
        project.scope2_emission = float(request.form['scope2'])
        project.scope3_emission = float(request.form['scope3'])

        db.session.commit()

        return redirect(url_for('view_project', id=project_id))

    return render_template('upload_esg.html', project=project)


@app.route('/view_esg/<int:project_id>', methods=['GET'])
def view_esg(project_id):
    project = Project.query.get_or_404(project_id)
    if not project:
        flash('Project not found!', 'danger')
        return redirect(url_for('home'))
    return render_template('view_esg.html', project=project)




@app.route('/upload_occupation/<int:supplier_id>', methods=['GET', 'POST'])
def upload_occupation(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if request.method == 'POST':
        try:
            if supplier.checkpoint < 3:  # Only allow a max of 3 checkpoints
                occupation_rate = float(request.form.get('occupation_rate'))
                facing_blocks = 'facing_blocks' in request.form
                supplier.occupation_rate = occupation_rate
                supplier.facing_blocks = facing_blocks
                supplier.checkpoint += 1  # Increment checkpoint number
                db.session.commit()
                flash('Occupation data uploaded successfully!', 'success')
                return redirect(url_for('view_occupation', supplier_id=supplier_id))
            else:
                flash('Maximum checkpoints reached.', 'info')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('upload_occupation.html', supplier=supplier)


@app.route('/view_occupation/<int:supplier_id>', methods=['GET'])
def view_occupation(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    occupation_data = {
        'occupation_rate': [supplier.occupation_rate],  # Assuming this data is saved for each checkpoint
        'facing_blocks': [1 if supplier.facing_blocks else 0],
        'checkpoint': supplier.checkpoint
    }

    return render_template('view_occupation.html', data=occupation_data)

@app.route('/upload_geopolitical/<int:supplier_id>', methods=['GET', 'POST'])
def upload_geopolitical(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if request.method == 'POST':
        risk_description = request.form.get('risk_description')
        if risk_description:
            new_risk = GeopoliticalRisk(description=risk_description, supplier_id=supplier_id)
            db.session.add(new_risk)
            db.session.commit()
            flash('Geopolitical risk added successfully!', 'success')
            return redirect(url_for('view_geopolitical'))  # Redirect to view geopolitical risks
        else:
            flash('Please provide a valid risk description.', 'warning')
    return render_template('upload_geopolitical.html', supplier=supplier)


@app.route('/view_geopolitical', methods=['GET'])
def view_geopolitical():
    suppliers = Supplier.query.all()  # Fetching all suppliers
    return render_template('view_geopolitical.html', suppliers=suppliers)


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
with app.app_context():
    db.create_all()