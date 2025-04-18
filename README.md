# Documentation

## Presentation
<p align="left">
  <a href="https://docs.google.com/presentation/d/1XAVLdmoZwuCC4ot5t-BM7qtA7b58TUdIf6kfdcoh20o/edit?usp=sharing" target="_blank">
    <img src="https://img.shields.io/badge/Open%20Slides-blue?style=for-the-badge" alt="Slides">
  </a>
</p>

## Video
<p align="left">
  <a href="https://drive.google.com/file/d/1AKJwu7iaXruduoMPH0bK47lWcvgU9AUs/view?usp=sharing" target="_blank">
    <img src="https://img.shields.io/badge/Open%20Video-olive?style=for-the-badge" alt="Video">
  </a>
</p>

## Github
Please clone the main branch since it contains the latest stable version.

<p align="left">
  <a href="https://github.com/FabianChristopher/DelveDeep.git" target="_blank">
    <img src="https://img.shields.io/badge/Open%20Code-orange?style=for-the-badge" alt="Code">
  </a>
</p>

## Requirements
- Open terminal 
- Activate your venv (optional but recommended)
- Run the following command
    ```
    pip3 install flask gradio requests openai
    ```

## How to Run
- Create a .env file in your root directory
- Save two OpenAI API Keys there. 

    ```
    OPENAI_API_KEY_1 = "<YOUR_OPENAI_KEY_1>"
    OPENAI_API_KEY_2 = "<YOUR_OPENAI_KEY_2>" 
    ```

- Open a terminal in your root directory and run the following to boot up your Backend.

    ```
    python app.py
    ```
- Open another terminal in your root directory and run the following to boot up your Frontend.

    ```
    python gradio_frontend.py
    ```
      
- Start up your Live Server to demo the Application.

## Making Contributions
- Contributions are welcome, but before you do, please follow these steps.
- Create a .gitignore file in your root directory.
- Paste the following in your .gitignore file and save it.

    ```
    # Ignore Python cache files
    __pycache__/
    *.pyc
    *.pyo

    # Ignore environment files
    .env
    ```
- Now you can push your changes to Github!
- Make sure to push changes to your named branch and not to main.

### 💖 Developed with love by Team ScholarWiz (Fabian Christopher, Shashwat Singh, Madhumita Kolukuluri)
