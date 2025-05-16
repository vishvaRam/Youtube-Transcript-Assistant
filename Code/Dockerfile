# Use a PyTorch base image
FROM python:3.11.12-slim

# Set the working directory
WORKDIR /workdir

# Install Python dependencies
COPY . .

# Update package lists
RUN apt-get update && apt-get install -y git curl

# Install Python dependencies
RUN pip install --upgrade pip -r requirements.txt

# Expose the port Streamlit will run on
EXPOSE 8501

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Set the default command
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
