from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import pandas as pd
import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from sklearn.cluster import KMeans
import io
import base64
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

app = Flask(__name__)

# Create a static folder for saving output files
if not os.path.exists('static'):
    os.makedirs('static')

# Route for index
@app.route('/')
def index():
    return render_template('index.html')

# Route for documentation
@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

# Route to handle the file upload and processing
@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    # Read the uploaded file
    df = pd.read_csv(file)

    # Generate molecular fingerprints (Morgan fingerprints)
    mols = [Chem.MolFromSmiles(smiles) for smiles in df['SMILES']]
    fps = [AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048) for mol in mols]

    # Convert the fingerprints to a numpy array
    fps_np = []
    for fp in fps:
        arr = np.zeros((1,))
        DataStructs.ConvertToNumpyArray(fp, arr)
        fps_np.append(arr)

    fps_np = np.array(fps_np)

    # Perform K-means clustering
    num_clusters = int(request.form['num_clusters'])
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    clusters = kmeans.fit_predict(fps_np)

    # Add cluster assignments to the dataframe
    df['Cluster'] = clusters

    # Save the clustering results to a new CSV file in the static folder
    output_csv = os.path.join('static', 'cluster_results.csv')
    df.to_csv(output_csv, index=False)

    # Perform PCA for 2D visualization
    pca = PCA(n_components=2)
    fps_pca = pca.fit_transform(fps_np)

    # Generate a scatter plot for visualization
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(fps_pca[:, 0], fps_pca[:, 1], c=clusters, cmap='rainbow')
    plt.colorbar(scatter)
    plt.title('Molecular Clusters (PCA)')
    plt.xlabel('PCA 1')
    plt.ylabel('PCA 2')

    # Save the plot to a PNG image in memory
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode()

    # Render the result.html with image and link to download CSV
    return render_template('result.html', img_data=img_base64, csv_download=output_csv, clustered_data=df.to_html())

# Route for downloading the clustering CSV
@app.route('/download_csv')
def download_csv():
    return send_file('static/cluster_results.csv', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
