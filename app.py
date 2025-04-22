from flask import Flask, render_template, request, jsonify
from optimizer import compute_route

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        start = data['start']
        end = data['end']
        price = float(data['price'])
        mode = data['mode']
        speed = float(data['speed'])

        result, error = compute_route(start, end, price, mode, speed)

        if error:
            return jsonify({'error': error}), 400

        return jsonify({
            'shortest': {
                'distance': round(result['shortest']['distance'], 2),
                'time_hr': int(result['shortest']['time']),
                'time_min': int((result['shortest']['time'] % 1) * 60),
                'cost': round(result['shortest']['cost'], 2),
                'start_coords': result['shortest']['start_coords'],
                'end_coords': result['shortest']['end_coords']
            },
            'second_shortest': {
                'distance': round(result['second_shortest']['distance'], 2),
                'time_hr': int(result['second_shortest']['time']),
                'time_min': int((result['second_shortest']['time'] % 1) * 60),
                'cost': round(result['second_shortest']['cost'], 2)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/map')
def display_map():
    return render_template("map.html")

if __name__ == '__main__':
    app.run(debug=True)