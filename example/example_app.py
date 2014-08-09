from flask import *
import portauthority

app = Flask(__name__)
app.debug = True

@app.route('/')
def home():
    return redirect(url_for('find_stop'))
    
@app.route('/find', methods=['GET', 'POST'])
def find_stop():
    if request.method == 'POST':
        busroute = request.form['busroute']
        stops = portauthority.get_route(busroute).stops
        return render_template('stop_list.html', stops=stops)
    elif request.method == 'GET':
        return render_template('find_stop.html')
    
@app.route('/stop/<stopid>')    
def arrival_info(stopid):
    next_stops = portauthority.next_bus(stopid)
    return render_template('arrival.html', arrivals=list(next_stops))
    
if __name__ == '__main__':
    app.run()    