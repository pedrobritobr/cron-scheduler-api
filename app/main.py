from flask import Flask, request, jsonify
import os
import json
from crontab import CronTab
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

def validar_cron_expression(cron_expression):
    partes = cron_expression.split()
    if len(partes) != 5:
        return False

    minutos, horas, dias, meses, dias_semana = partes

    def validar_intervalo(valor, minimo, maximo):
        partes = valor.split(',')
        for parte in partes:
            if '-' in parte:
                inicio, fim = map(int, parte.split('-'))
                if not (minimo <= inicio <= fim <= maximo):
                    return False
            else:
                if not (minimo <= int(parte) <= maximo):
                    return False
        return True

    return (
        validar_intervalo(minutos, 0, 59) and
        validar_intervalo(horas, 0, 23) and
        validar_intervalo(dias, 1, 31) and
        validar_intervalo(meses, 1, 12) and
        validar_intervalo(dias_semana, 0, 6)
    )

def is_valid_fields(*fields):
    return all(fields)

def generate_curl_command(msg, tel_number):
    task_data = {
        "chatId": f"{tel_number}@c.us",
        "content": msg,
        "contentType": "string"
    }

    send_url = "http://34.30.179.35:3000/client/sendMessage/imwbot"
    x_api_key = os.getenv('X_API_KEY')
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': x_api_key
    }
    headers_str = ' '.join([f"-H '{k}: {v}'" for k, v in headers.items()])
    data_str = f"-d '{json.dumps(task_data, ensure_ascii=False)}'"
    return f"curl -X POST {send_url} {headers_str} {data_str}"

def publish_cron(cron_expression, curl_command):
    cron = CronTab(user=True)
    try:
        job = cron.new()
        job.setall(cron_expression)
        job.command = curl_command
        cron.write()
    except KeyError as e:
        print(e)
        return jsonify({"error": "Cron string inválida."}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": "Erro ao agendar tarefa."}), 500

def schedule_task(data):
    cron_expression = data.get('cron', None)
    msg = data.get('msg', None)
    tel_number = data.get('tel_number', None)

    if not is_valid_fields(cron_expression, msg, tel_number):
        return jsonify({"error": "Parâmetros vazios."}), 400

    curl_command = generate_curl_command(msg, tel_number)

    publish_cron(cron_expression, curl_command)

    return jsonify({"message": "Tarefa agendada com sucesso!"}), 200


@app.route('/schedule', methods=['POST'])
def post_schedule():
    data = request.get_json()
    return schedule_task(data)


@app.route('/schedule', methods=['GET'])
def get_schedule():
    cron = CronTab(user=True)
    tasks = []
    for job in cron:
        tasks.append({
            'cron': str(job),
            'command': job.command
        })
    return jsonify(tasks)

@app.route('/schedule', methods=['DELETE'])
def delete_schedule():
    cron = CronTab(user=True)
    cron.remove_all()
    cron.write()
    return jsonify({"message": "Todas as tarefas foram removidas."})


if __name__ == "__main__":
    # app.run(debug=True)
    schedule_task({
        'cron': 'x * * * *',
        'msg': 'Olá, mundo! Python',
        'tel_number': '5522998979168'
    })
