import glob
import os
import joblib
import pickle
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# ==============================
# CONFIGURAÇÕES
# ==============================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# ==============================
# CARREGAR MODELO E ARTEFATOS UMA VEZ
# ==============================
model = joblib.load("dropout_prediction_model/ensemble_model.pkl")

with open("dropout_prediction_model/optimal_threshold.pkl", "rb") as f:
    threshold = pickle.load(f)

with open("dropout_prediction_model/label_encoders.pkl", "rb") as f:
    label_encoders = pickle.load(f)

with open("dropout_prediction_model/feature_names.pkl", "rb") as f:
    feature_names = pickle.load(f)

with open("dropout_prediction_model/columns_to_drop.pkl", "rb") as f:
    cols_to_drop = pickle.load(f)


# ==============================
# FUNÇÕES AUXILIARES
# ==============================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clear_upload_folder():
    """Remove todos os arquivos CSV da pasta de upload"""
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.lower().endswith('.csv'):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except OSError:
                    pass


def preprocessar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o mesmo pré-processamento usado no treinamento"""
    df = df.copy()

    df = df.drop(columns=cols_to_drop, errors='ignore')

    for coluna, encoder in label_encoders.items():
        if coluna in df.columns:
            try:
                df[coluna] = encoder.transform(df[coluna])
            except ValueError:
                df[coluna] = -1

    df['Total approved'] = (
        df['Curricular units 1st sem (approved)'] +
        df['Curricular units 2nd sem (approved)']
    )
    df['Average grade'] = (
        df['Curricular units 1st sem (grade)'] +
        df['Curricular units 2nd sem (grade)']
    ) / 2
    df['Approval rate'] = df['Total approved'] / (
        df['Curricular units 1st sem (enrolled)'] +
        df['Curricular units 2nd sem (enrolled)']
    ).replace(0, np.nan)
    df['Grade diff'] = (
        df['Curricular units 2nd sem (grade)'] -
        df['Curricular units 1st sem (grade)']
    )
    df['Failed any sem'] = (
        (df['Curricular units 1st sem (approved)'] == 0) |
        (df['Curricular units 2nd sem (approved)'] == 0)
    ).astype(int)

    # 4. Garantir features
    for feature in feature_names:
        if feature not in df.columns:
            df[feature] = 0

    # 5. Ordem correta
    return df[feature_names]


def prever_dropout(df: pd.DataFrame):
    dados_processados = preprocessar_dados(df)
    probabilidades = model.predict_proba(dados_processados)[:, 1]
    predicoes = (probabilidades >= threshold).astype(int)
    confianca = np.abs(probabilidades - 0.5) * 2
    return predicoes, probabilidades, confianca


# ==============================
# ROTAS
# ==============================
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Apenas arquivos CSV são permitidos'}), 400

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        clear_upload_folder()

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # =========================
        # PROCESSAR CSV
        # =========================
        df = pd.read_csv(filepath)

        preds, probs, confs = prever_dropout(df)

        df['Prediction'] = preds
        df['Probability'] = probs
        df['Confidence'] = confs

        result_filename = f"resultado_{filename}"
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        df.to_csv(result_path, index=False)

        file_size = os.path.getsize(filepath)
        file_size_mb = round(file_size / (1024 * 1024), 2)

        return jsonify({
            'success': True,
            'message': f'Arquivo "{filename}" enviado e processado com sucesso!',
            'filename': filename,
            'size': f'{file_size_mb} MB',
            'result_file': result_filename
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'}), 500

@app.route('/data', methods=['GET'])
def get_data():
    try:
        csv_files = glob.glob("uploads/resultado_*.csv")
        
        if not csv_files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo de resultado encontrado.'}), 404
        
        csv_file = csv_files[0]
        
        df = pd.read_csv(csv_file)
        last_three_columns = df.iloc[:, -3:]

        result = []
        for index, row in last_three_columns.iterrows():
            result.append({
                'Prediction': int(row.iloc[0]),
                'Probability': round(float(row.iloc[1]), 4),
                'Confidence': round(float(row.iloc[2]), 4)
            })
        
        return jsonify({
            'success': True, 
            'data': result
        })
    except FileNotFoundError:
        return jsonify({'success': False, 'message': 'Nenhum arquivo de resultado encontrado.'}), 404 
    except pd.errors.EmptyDataError:
        return jsonify({'success': False, 'message': 'Arquivo de resultado vazio.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao ler os dados: {str(e)}'}), 500
        
    except FileNotFoundError:
        return jsonify({
            "success": False,
            "error": "Pasta uploads não encontrada"
        }), 404
        
    except pd.errors.EmptyDataError:
        return jsonify({
            "success": False,
            "error": "Arquivo CSV está vazio"
        }), 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Erro ao processar arquivo: {str(e)}"
        }), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'message': 'Arquivo muito grande. Tamanho máximo: 16MB'
    }), 413


if __name__ == '__main__':
    app.run(debug=True)
