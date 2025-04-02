# Documentation

## Requirements
- Open terminal 
- Activate your venv (optional but recommended)
- Run the following command
    ```
    pip3 install flask gradio requests openai
    ```

## How to Run
- Create a .env file in your root directory
- Save your OpenAI API Keys there. 

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
      
- Either open the Local link or the Hosted link in the second terminal to demo the Application.

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

### 💖 Developed with love by Fabian Christopher
