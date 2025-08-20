const uploadArea = document.querySelector('.upload-area');
const fileInput = document.getElementById('fileInput');
const loading = document.getElementById('loading');
const message = document.getElementById('message');
const fileInfo = document.getElementById('fileInfo');

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        uploadFile();
    }
});

fileInput.addEventListener('change', uploadFile);

function showMessage(text, type) {
    message.textContent = text;
    message.className = `message ${type}`;
    message.style.display = 'block';
    setTimeout(() => {
        message.style.display = 'none';
    }, 5000);
}

function showFileInfo(filename, size) {
    fileInfo.innerHTML = `
        <strong>Arquivo enviado:</strong> ${filename}<br>
        <strong>Tamanho:</strong> ${size}
    `;
    fileInfo.style.display = 'block';
}

function uploadFile() {
    const file = fileInput.files[0];
    
    if (!file) {
        showMessage('Por favor, selecione um arquivo', 'error');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
        showMessage('Apenas arquivos CSV são permitidos', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    loading.style.display = 'block';
    message.style.display = 'none';
    fileInfo.style.display = 'none';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loading.style.display = 'none';
        
        if (data.success) {
            showMessage(data.message, 'success');
            showFileInfo(data.filename, data.size);
            location.reload(); 
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        loading.style.display = 'none';
        showMessage('Erro ao enviar arquivo: ' + error.message, 'error');
    });
}

async function carregarTabela() {
    try {
        const response = await fetch("http://127.0.0.1:5000/data");
        if (!response.ok) throw new Error("Erro ao buscar os dados");

        const jsonData = await response.json();
        const tabela = document.querySelector("#tabelaAlunos tbody");
        tabela.innerHTML = "";

        jsonData.data.forEach((aluno, index) => {
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            tdId.textContent = `Aluno ${index + 1}`;

            const tdPred = document.createElement("td");
            tdPred.textContent = aluno.Prediction === 1 
                ? "Chance de Evasão" 
                : "Baixa Chance de Evasão";

            const tdProb = document.createElement("td");
            tdProb.textContent = `${Math.round(aluno.Probability * 100)}%`;

            tr.appendChild(tdId);
            tr.appendChild(tdPred);
            tr.appendChild(tdProb);

            tabela.appendChild(tr);
        });

    } catch (error) {
        console.error("Erro:", error);
    }
}

document.addEventListener("DOMContentLoaded", carregarTabela);

let chartEvasao;

async function carregarTabelaEGrafico() {
    try {
        const response = await fetch("http://127.0.0.1:5000/data");
        if (!response.ok) throw new Error("Erro ao buscar os dados");

        const jsonData = await response.json();
        const tabela = document.querySelector("#tabelaAlunos tbody");
        tabela.innerHTML = "";

        let acima80 = 0;
        let abaixo80 = 0;

        jsonData.data.forEach((aluno, index) => {
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            tdId.textContent = `Aluno ${index + 1}`;

            const tdPred = document.createElement("td");
            tdPred.textContent = aluno.Prediction === 1 
                ? "Chance de Evasão" 
                : "Baixa Chance de Evasão";

            const tdProb = document.createElement("td");
            const probPct = Math.round(aluno.Probability * 100);
            tdProb.textContent = `${probPct}%`;

            tr.appendChild(tdId);
            tr.appendChild(tdPred);
            tr.appendChild(tdProb);
            tabela.appendChild(tr);

            if (probPct >= 80) {
                acima80++;
            } else {
                abaixo80++;
            }
        });

        const ctx = document.getElementById("graficoEvasao").getContext("2d");

        if (chartEvasao) {
            chartEvasao.destroy();
        }

        chartEvasao = new Chart(ctx, {
            type: "pie",
            data: {
                labels: ["Maior Chance de Evasão", "Menor Chance de Evasão"],
                datasets: [{
                    data: [acima80, abaixo80],
                    backgroundColor: ["#e74c3c", "#2ecc71"],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "bottom"
                    }
                }
            }
        });

    } catch (error) {
        console.error("Erro:", error);
    }
}

document.addEventListener("DOMContentLoaded", carregarTabelaEGrafico);

document.addEventListener("DOMContentLoaded", () => {
    const labels = [
        "Approval rate",
        "Curricular units 2nd sem (approved)",
        "Total approved",
        "Tuition fees up to date",
        "Curricular units 2nd sem (enrolled)"
    ];

    const valores = [
        0.256662,
        0.124749,
        0.108954,
        0.053630,
        0.029429
    ];

    const ctx = document.getElementById("graficoTop5").getContext("2d");

    new Chart(ctx, {
        type: "radar",
        data: {
            labels: labels,
            datasets: [{
                label: "Importância das Variáveis",
                data: valores,
                backgroundColor: "rgba(52, 152, 219, 0.25)",
                borderColor: "rgba(41, 128, 185, 0.9)",
                borderWidth: 2,
                pointBackgroundColor: "rgba(41, 128, 185, 1)",
                pointBorderColor: "#fff",
                pointRadius: 5,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: "Top 5 Variáveis Mais Importantes",
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.formattedValue}`;
                        }
                    }
                }
            },
            scales: {
                r: {
                    angleLines: { color: "rgba(0,0,0,0.1)" },
                    grid: { color: "rgba(0,0,0,0.05)" },
                    suggestedMin: 0,
                    suggestedMax: 0.3,
                    ticks: {
                        stepSize: 0.05,
                        backdropColor: "transparent"
                    },
                    pointLabels: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: "easeOutElastic"
            }
        }
    });
});

