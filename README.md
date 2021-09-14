# Automated Natural Language Dictionary System

This dictionary can contain a list of lexemes in alphabetical order which contain links to other lexemes that can make up phrases together.
Before adding new words or editing the database the user is prompted to register or log in the system.
The user can input a text and the system parses words and phrases and adds new words and their connections to the dictionary.
The user can add a single word or link two existing words together.
The language of the system is English.

### Demo: [Video](https://user-images.githubusercontent.com/44346252/114877622-1be74380-9e08-11eb-807a-0d9c4a4a3c48.mp4)

### Report: [Google Doc](https://docs.google.com/document/d/1Cz1bmbvf6uIFuWBt5yoaTZTb6476Qx_rg5P6oRzOHiE/edit?usp=sharing)

---

### Commands to run the project:
-  `venv\Scripts\activate`
-  `set FLASK_APP=dictionary`
-  `set FLASK_ENV=development`
-  `flask init-db`
-  `flask run`
