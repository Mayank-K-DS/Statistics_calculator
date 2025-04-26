from flask import Flask, request, render_template, redirect, url_for, flash
import csv
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import math

app = Flask(__name__)
app.secret_key = "statistical_calculator_key"

def calculate_mean(data):
    """Calculate the mean of a list of numbers."""
    if not data:
        return 0
    total = sum(data)
    return total / len(data)

def calculate_variance(data):
    """Calculate the variance of a list of numbers."""
    if len(data) <= 1:
        return 0
    mean = calculate_mean(data)
    squared_diff_sum = sum((x - mean) ** 2 for x in data)
    return squared_diff_sum / (len(data) - 1)  # Sample variance

def calculate_std_dev(data):
    """Calculate the standard deviation of a list of numbers."""
    return math.sqrt(calculate_variance(data))

def calculate_confidence_interval(data, confidence=0.95):
    """Calculate the confidence interval for the mean of a list of numbers."""
    if len(data) <= 1:
        return (0, 0)
    
    # Z-values for common confidence levels
    z_values = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576
    }
    
    mean = calculate_mean(data)
    std_dev = calculate_std_dev(data)
    z = z_values.get(confidence, 1.96)  # Default to 95% if not found
    
    margin_of_error = z * (std_dev / math.sqrt(len(data)))
    
    return (mean - margin_of_error, mean + margin_of_error)

def create_histogram(data):
    """Create a histogram of the data with mean and confidence intervals."""
    fig = Figure(figsize=(6, 4))
    ax = fig.add_subplot(1, 1, 1)
    
    # Calculate number of bins using Sturges' rule
    num_bins = int(1 + 3.322 * math.log10(len(data))) if data else 5
    
    ax.hist(data, bins=num_bins, color='skyblue', edgecolor='black', alpha=0.7)
    ax.set_title('Data Distribution')
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency')
    
    # Add vertical line for mean
    mean = calculate_mean(data)
    ax.axvline(x=mean, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean:.2f}')
    
    # Add confidence intervals
    if len(data) > 1:
        # 90% Confidence Interval
        ci_90_lower, ci_90_upper = calculate_confidence_interval(data, 0.90)
        ax.axvspan(ci_90_lower, ci_90_upper, alpha=0.1, color='blue', label='90% CI')
        
        # 95% Confidence Interval
        ci_95_lower, ci_95_upper = calculate_confidence_interval(data, 0.95)
        ax.axvspan(ci_95_lower, ci_95_upper, alpha=0.1, color='green', label='95% CI')
        
        # 99% Confidence Interval
        ci_99_lower, ci_99_upper = calculate_confidence_interval(data, 0.99)
        ax.axvspan(ci_99_lower, ci_99_upper, alpha=0.1, color='purple', label='99% CI')
    
    ax.legend(loc='best')
    
    # Convert plot to PNG image
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    
    # Encode PNG image to base64 string
    data_uri = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{data_uri}"

def process_data(data_string):
    """Process comma-separated string into a list of floats."""
    try:
        # Split by comma and convert to float
        data = [float(x.strip()) for x in data_string.split(',') if x.strip()]
        return data
    except ValueError:
        return None

def calculate_statistics(data):
    """Calculate all statistics for the given data."""
    if not data or len(data) == 0:
        return None
    
    mean = calculate_mean(data)
    variance = calculate_variance(data)
    std_dev = calculate_std_dev(data)
    ci_90 = calculate_confidence_interval(data, 0.90)
    ci_95 = calculate_confidence_interval(data, 0.95)
    ci_99 = calculate_confidence_interval(data, 0.99)
    
    histogram = create_histogram(data)
    
    return {
        'data': data,
        'count': len(data),
        'mean': mean,
        'variance': variance,
        'std_dev': std_dev,
        'ci_90': ci_90,
        'ci_95': ci_95,
        'ci_99': ci_99,
        'histogram': histogram
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    
    if request.method == 'POST':
        input_type = request.form.get('input_type')
        
        if input_type == 'manual':
            data_string = request.form.get('manual_data', '')
            data = process_data(data_string)
            
            if data is None or len(data) == 0:
                flash('Please enter valid comma-separated numbers.')
                return redirect(url_for('index'))
                
            result = calculate_statistics(data)
            
        elif input_type == 'csv_column':
            if 'csv_file_column' not in request.files:
                flash('No file selected.')
                return redirect(url_for('index'))
                
            file = request.files['csv_file_column']
            column_name = request.form.get('column_name', '').strip()
            
            if file.filename == '':
                flash('No file selected.')
                return redirect(url_for('index'))
                
            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file.')
                return redirect(url_for('index'))
                
            if not column_name:
                flash('Please specify a column name.')
                return redirect(url_for('index'))
                
            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
                csv_reader = csv.DictReader(stream)
                
                if column_name not in csv_reader.fieldnames:
                    flash(f'Column "{column_name}" not found in the CSV file.')
                    return redirect(url_for('index'))
                
                # Extract data from specified column
                data = []
                for row in csv_reader:
                    try:
                        value = row[column_name].strip()
                        if value:
                            data.append(float(value))
                    except (ValueError, KeyError):
                        continue  # Skip non-numeric values
                
                if len(data) == 0:
                    flash(f'No valid numeric data found in column "{column_name}".')
                    return redirect(url_for('index'))
                    
                result = calculate_statistics(data)
                
            except Exception as e:
                flash(f'Error processing CSV file: {str(e)}')
                return redirect(url_for('index'))
    
    return render_template('index.html', result=result)

@app.template_filter('format_float')
def format_float(value):
    return f"{value:.4f}" if isinstance(value, (int, float)) else value

if __name__ == '__main__':
    app.run(debug=True)