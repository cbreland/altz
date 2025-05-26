document.addEventListener('DOMContentLoaded', () => {
    const tickerInput = document.getElementById('tickerInput');
    const getScoreButton = document.getElementById('getScoreButton');
    const errorMessagesDiv = document.getElementById('errorMessages');
    const currentZScoreDiv = document.getElementById('currentZScore');
    const historicalChartContainer = document.getElementById('historicalChartContainer');
    const historicalErrorMessagesDiv = document.getElementById('historicalErrorMessages');
    const historicalZScoreChartCtx = document.getElementById('historicalZScoreChart').getContext('2d');
    const loadingSpinner = document.getElementById('loadingSpinner'); // Get spinner element
    let currentZScoreChartInstance = null;

    getScoreButton.addEventListener('click', fetchData);
    tickerInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            fetchData();
        }
    });

    tickerInput.addEventListener('input', () => {
        // Clear client-side validation error when user types
        if (errorMessagesDiv.textContent.includes("Ticker symbol cannot be empty") || 
            errorMessagesDiv.textContent.includes("Invalid ticker format")) {
            errorMessagesDiv.innerHTML = '';
            errorMessagesDiv.style.display = 'none';
        }
    });

    function clearResults() {
        errorMessagesDiv.innerHTML = '';
        errorMessagesDiv.style.display = 'none';
        currentZScoreDiv.innerHTML = '';
        historicalErrorMessagesDiv.innerHTML = '';
        historicalErrorMessagesDiv.style.display = 'none';
        if (currentZScoreChartInstance) {
            currentZScoreChartInstance.destroy();
            currentZScoreChartInstance = null;
        }
         historicalChartContainer.style.display = 'none'; // Hide chart container initially
    }

    function displayError(message, targetDivId = 'errorMessages') {
        const targetDiv = document.getElementById(targetDivId);
        if (targetDiv) {
            targetDiv.innerHTML = `<p>${message}</p>`; // Ensure message is wrapped in a <p> or similar for consistent styling if CSS expects it
            targetDiv.style.display = 'block';
        }
    }

    function getRiskAssessment(zScore) {
        if (zScore === null || zScore === undefined || isNaN(parseFloat(zScore))) {
            return { text: "N/A (Insufficient Data)", class: "" };
        }
        if (zScore > 2.99) return { text: "Safe Zone", class: "risk-safe" };
        if (zScore > 1.81) return { text: "Grey Zone (Caution)", class: "risk-grey" };
        return { text: "Distress Zone (High Risk)", class: "risk-distress" };
    }

    function displayCurrentZScore(data) {
        if (!data || data.z_score === undefined) {
            displayError('Invalid data format received for current Z-Score.', 'errorMessages');
            return;
        }

        const risk = getRiskAssessment(data.z_score);
        let html = `
            <p><strong>Ticker:</strong> ${data.ticker}</p>
            <p><strong>Altman Z-Score:</strong> <span class="z-score-value ${risk.class}">${data.z_score !== null ? data.z_score.toFixed(4) : 'N/A'}</span></p>
            <p><strong>Risk Assessment:</strong> <span class="${risk.class}">${risk.text}</span></p>
            <h3>Score Components (X-Factors):</h3>
            <ul>
                <li><strong>X1 (Working Capital / Total Assets):</strong> ${data.X1 !== null ? data.X1.toFixed(4) : 'N/A'}</li>
                <li><strong>X2 (Retained Earnings / Total Assets):</strong> ${data.X2 !== null ? data.X2.toFixed(4) : 'N/A'}</li>
                <li><strong>X3 (EBIT / Total Assets):</strong> ${data.X3 !== null ? data.X3.toFixed(4) : 'N/A'}</li>
                <li><strong>X4 (Market Cap / Total Liabilities):</strong> ${data.X4 !== null ? data.X4.toFixed(4) : 'N/A'}</li>
                <li><strong>X5 (Revenue / Total Assets):</strong> ${data.X5 !== null ? data.X5.toFixed(4) : 'N/A'}</li>
            </ul>
        `;

        if (data.raw_data && Object.keys(data.raw_data).length > 0) {
            html += `<h3>Key Financial Figures (from Gurufocus):</h3><table class="financial-data-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>`;
            for (const [key, value] of Object.entries(data.raw_data)) {
                const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); // Format key for display
                html += `<tr><td>${formattedKey}</td><td>${typeof value === 'number' ? '$' + value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : value}</td></tr>`;
            }
            html += `</tbody></table>`;
        }
        currentZScoreDiv.innerHTML = html;
    }
    
    function displayHistoricalZScoreChart(data) {
        if (currentZScoreChartInstance) {
            currentZScoreChartInstance.destroy();
            currentZScoreChartInstance = null;
        }
        
        if (!data || !data.historical_z_scores || data.historical_z_scores.length === 0) {
            historicalErrorMessagesDiv.innerHTML = '<p>No historical Z-Score data available for this ticker or period.</p>';
            historicalErrorMessagesDiv.style.display = 'block';
            historicalChartContainer.style.display = 'none';
            return;
        }
        
        historicalErrorMessagesDiv.innerHTML = ''; // Clear previous errors
        historicalErrorMessagesDiv.style.display = 'none';
        historicalChartContainer.style.display = 'block';

        const sortedScores = data.historical_z_scores.sort((a, b) => a.year - b.year);
        const labels = sortedScores.map(item => item.year);
        const zScores = sortedScores.map(item => item.z_score);
        // const x1Data = sortedScores.map(item => item.X1); // Keep for potential future use
        // const x2Data = sortedScores.map(item => item.X2);
        // const x3Data = sortedScores.map(item => item.X3);
        // const x4Data = sortedScores.map(item => item.X4);
        // const x5Data = sortedScores.map(item => item.X5);

        try {
            currentZScoreChartInstance = new Chart(historicalZScoreChartCtx, {
                type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Altman Z-Score',
                        data: zScores,
                        borderColor: 'rgb(54, 162, 235)', // Blue
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        tension: 0.1,
                        yAxisID: 'yZscore',
                    },
                    // Optional: Plot X-factors if needed, might need separate y-axes or normalization
                    // For simplicity, only Z-Score is plotted prominently. Others can be added.
                    // { label: 'X1', data: x1Data, borderColor: 'rgb(255, 99, 132)', tension: 0.1, yAxisID: 'yFactors', hidden: true },
                    // { label: 'X2', data: x2Data, borderColor: 'rgb(75, 192, 192)', tension: 0.1, yAxisID: 'yFactors', hidden: true },
                    // { label: 'X3', data: x3Data, borderColor: 'rgb(255, 205, 86)', tension: 0.1, yAxisID: 'yFactors', hidden: true },
                    // { label: 'X4', data: x4Data, borderColor: 'rgb(201, 203, 207)', tension: 0.1, yAxisID: 'yFactors', hidden: true },
                    // { label: 'X5', data: x5Data, borderColor: 'rgb(153, 102, 255)', tension: 0.1, yAxisID: 'yFactors', hidden: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Allow chart to shrink if container is small
                scales: {
                    yZscore: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Z-Score Value'
                        }
                    },
                    // yFactors: { // Example for a separate axis for X-factors if they were displayed
                    //     type: 'linear',
                    //     display: false, // Set to true if you want to show it
                    //     position: 'right',
                    //     grid: { drawOnChartArea: false, },
                    //     title: { display: true, text: 'X-Factor Values' }
                    // },
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(4);
                                }
                                return label;
                            }
                        }
                    },
                    legend: {
                        display: true,
                        // onClick: function(e, legendItem, legend) { // Allow toggling datasets
                        //     const index = legendItem.datasetIndex;
                        //     const ci = legend.chart;
                        //     if (ci.isDatasetVisible(index)) {
                        //         ci.hide(index);
                        //         legendItem.hidden = true;
                        //     } else {
                        //         ci.show(index);
                        //         legendItem.hidden = false;
                        //     }
                        // }
                    }
                }
            }
            });
        } catch (chartError) {
            console.error("Chart.js rendering error:", chartError);
            displayError('Failed to render historical Z-Score chart.', 'historicalErrorMessages');
            historicalChartContainer.style.display = 'none';
        }
    }

    async function fetchData() {
        const ticker = tickerInput.value.trim().toUpperCase();
        
        // Client-side validation
        if (!ticker) {
            displayError('Ticker symbol cannot be empty.', 'errorMessages');
            return;
        }
        // Basic format check: 1-6 alphanumeric characters (common for US tickers)
        if (!/^[A-Z0-9.]{1,10}$/.test(ticker)) { 
            displayError('Invalid ticker format. Use 1-10 uppercase letters, numbers, or periods (e.g., AAPL, MSFT, BRK.A).', 'errorMessages');
            return;
        }

        clearResults();
        getScoreButton.disabled = true;
        getScoreButton.textContent = 'Loading...';
        if(loadingSpinner) loadingSpinner.style.display = 'inline-block';

        let currentScoreSuccess = false;

        // Fetch Current Z-Score
        try {
            const currentResponse = await fetch(`/api/zscore/${ticker}`);
            if (!currentResponse.ok) {
                const errorData = await currentResponse.json();
                throw new Error(errorData.error || `Current Z-Score: HTTP error! status: ${currentResponse.status}`);
            }
            const currentData = await currentResponse.json();
            displayCurrentZScore(currentData);
            currentScoreSuccess = true;
        } catch (error) {
            console.error('Error fetching current Z-Score:', error);
            displayError(error.message, 'errorMessages');
            // Do not return here, still attempt to fetch historical data unless the error is critical (e.g. 404 on ticker)
        }

        // Fetch Historical Z-Score (even if current failed, as it uses a different source)
        try {
            const historicalResponse = await fetch(`/api/historical_zscore/${ticker}?years=5`);
            if (!historicalResponse.ok) {
                const errorData = await historicalResponse.json();
                throw new Error(errorData.error || `Historical Z-Score: HTTP error! status: ${historicalResponse.status}`);
            }
            const historicalData = await historicalResponse.json();
            displayHistoricalZScoreChart(historicalData);
        } catch (error) {
            console.error('Error fetching historical Z-Score:', error);
            // If current score also failed, historicalErrorMessages might be overwritten by current error.
            // We might want to append or have separate error divs if both fail.
            // For now, let's prioritize showing the historical error if current one was already shown or if current succeeded.
            if (currentScoreSuccess || !errorMessagesDiv.textContent) {
                 displayError(error.message, 'historicalErrorMessages');
            } else {
                // If errorMessagesDiv already has an error from current score, append or log to console
                console.error("Historical data fetch also failed:", error.message);
                 // Optionally append to the main error div if distinct historical error div is not prominent enough
                // errorMessagesDiv.innerHTML += `<br><p>Historical Data Error: ${error.message}</p>`;
            }
        } finally {
            getScoreButton.disabled = false;
            getScoreButton.textContent = 'Get Score';
            if(loadingSpinner) loadingSpinner.style.display = 'none';
        }
    }
});
