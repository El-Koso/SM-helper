## Лицензия. Этот проект распространяется под лицензией GPLv3. Подробности можно найти в файле COPYING


import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sqlite3
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from tkinter import PhotoImage

import re

import tkinter as tk
from tkinter import ttk

def show_license():
    """Отображает текст лицензии из файла COPYING в новом окне с возможностью прокрутки."""
    try:
        with open("COPYING", "r", encoding="utf-8") as file:
            license_text = file.read()

        license_window = tk.Toplevel(root)
        license_window.title("Лицензия")

        # Создаем текстовый виджет
        text_widget = tk.Text(license_window, wrap=tk.WORD)
        text_widget.insert(tk.END, license_text)
        text_widget.config(state=tk.DISABLED)  # Запрещаем редактирование

        # Создаем полосу прокрутки
        scrollbar = tk.Scrollbar(license_window, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)

        # Размещаем виджеты
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    except FileNotFoundError:
        show_message("Файл лицензии COPYING не найден!", "error")
    except Exception as e:
        show_message(f"Ошибка при чтении файла лицензии: {e}", "error")



def validate_snils(snils):
    """
    Проверяет корректность СНИЛС.
    :param snils: СНИЛС в формате 'XXX-XXX-XXX YY' или 'XXXXXXXXXYY'.
    :return: True, если СНИЛС корректен, иначе False.
    """
    # Проверка формата
    if not re.match(r"^\d{3}-\d{3}-\d{3} \d{2}$", snils) and not re.match(r"^\d{11}$", snils):
        return False

    # Убираем все нецифровые символы
    snils_clean = re.sub(r"[-\s]", "", snils)

    # Проверка длины
    if len(snils_clean) != 11:
        return False

    # Разделяем основную часть и контрольную сумму
    main_part = snils_clean[:9]
    control_sum = int(snils_clean[-2:])

    # Вычисляем контрольную сумму
    total = 0
    for i, digit in enumerate(main_part, start=1):
        total += int(digit) * (10 - i)

    # Проверка контрольной суммы
    if total < 100:
        return total == control_sum
    elif total == 100 or total == 101:
        return control_sum == 0
    else:
        return (total % 101) == control_sum


def validate_date(date_str):
    """Проверяет корректность формата даты."""
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False
        

def show_position_options(event):
    """Отображает список доступных должностей при нажатии на кнопку."""
    try:
        with open("positions.txt", "r") as file:
            positions = [pos.strip() for pos in file.readlines()]

        position_window = tk.Toplevel(root)
        position_window.title("Выберите должность")

        position_listbox = tk.Listbox(position_window, width=60, height=20)
        position_listbox.pack(padx=5, pady=10, fill="both", expand=True)

        for position in positions:
            position_listbox.insert(tk.END, position)

        position_listbox.bind("<<ListboxSelect>>", lambda event: select_position(position_listbox))
        position_window.mainloop()
    except FileNotFoundError:
        show_message("Файл positions.txt не найден.", "error")
    except Exception as e:
        show_message(f"Ошибка: {e}", "error")

def select_position(listbox):
    """Заполняет поле position_entry выбранной должностью."""
    selected_index = listbox.curselection()
    if selected_index:
        selected_position = listbox.get(selected_index)
        position_entry.delete(0, tk.END)
        position_entry.insert(0, selected_position)
        listbox.master.destroy()
        
#Функция для получения СНИЛС из базы данных
def get_user_data_from_db(conn, surname, name, patronymic):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT snils, position FROM users WHERE surname = ? AND name = ? AND patronymic = ?", (surname, name, patronymic))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]  # Возвращаем СНИЛС и профессию
        return None, None
    except sqlite3.Error as e:
        show_message(f"Ошибка базы данных: {e}", "error")
        return None, None

#Функция для предложения автоматического заполнения СНИЛС
def suggest_autofill_data(conn, surname, name, patronymic):
    snils, position = get_user_data_from_db(conn, surname, name, patronymic)
    if snils or position:
        response = messagebox.askyesno(
            "Автозаполнение данных",
            f"Найдена запись с такой же фамилией, именем и отчеством.\n"
            f"СНИЛС: {snils}\n"
            f"Профессия: {position}\n\n"
            "Заполнить поля СНИЛС и Профессия автоматически?"
        )
        if response:
            if snils:
                snils_entry.delete(0, tk.END)
                snils_entry.insert(0, snils)
            if position:
                position_entry.delete(0, tk.END)
                position_entry.insert(0, position)

def show_message(message, message_type="info"):
    """Отображает сообщение в отдельном окне, которое закрывается через 2 секунды."""
    top = tk.Toplevel(root)
    top.title("Сообщение")
    top.attributes('-topmost', True)   # Эта строка гарантирует, что окно всегда наверху.
    
    label = ttk.Label(top, text=message, wraplength=300)
    label.pack(pady=20)
    if message_type == "error":
        label.config(foreground="red")
    elif message_type == "success":
        label.config(foreground="green")
    top.transient(root)
    top.grab_set()
    top.after(900, top.destroy)      # Тут можно задать время показа сервисного окна
    top.mainloop()

def submit_data(conn):
    """Отправляет данные в базу данных, проверяя заполненные поля и чекбокс."""
    try:
        surname = surname_entry.get()
        name = name_entry.get()
        patronymic = patronymic_entry.get()
        snils = snils_entry.get()
        isForeignSnils = 1 if isForeignSnils_var.get() else 0
        foreignSnils = foreignSnils_entry.get()
        citizenship = citizenship_entry.get()
        position = position_entry.get()
        org_inn = org_inn_entry.get()
        org_title = org_title_entry.get()
        employer_org_inn = employer_org_inn_entry.get()
        employer_org_title = employer_org_title_entry.get()
        selected_program_ids = [int(learn_program_listbox.get(i).split('.')[0]) for i in learn_program_listbox.curselection()]
        is_passed = 1 if is_passed_var.get() else 0
        protocol_number = protocol_number_entry.get()
        exam_date = exam_date_entry.get()
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        required_fields = [surname, name, snils, exam_date, protocol_number]
        if not all(required_fields):
            show_message("Все обязательные поля не заполнены.", "error")
            return

        if not validate_snils(snils):
            show_message("Неверный СНИЛС.", "error")
            return

        if not validate_date(exam_date):
            show_message("Неверный формат даты.", "error")
            return

        if '/' in protocol_number:
            show_message("Номер протокола не должен содержать символа '/'.", "error")
            return

        if not selected_program_ids:
            show_message("Выберите хотя бы одну учебную программу.", "error")
            return

        for program_id in selected_program_ids:
            conn.execute(
                '''
                INSERT INTO users (
                    surname, name, patronymic, snils, isForeignSnils, foreignSnils, citizenship,
                    position, org_inn, org_title, employer_org_inn, employer_org_title,
                    learn_program_id, is_passed, protocol_number, exam_date, entry_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    surname, name, patronymic, snils, isForeignSnils, foreignSnils, citizenship,
                    position, org_inn, org_title, employer_org_inn, employer_org_title,
                    program_id, is_passed, protocol_number, exam_date, now
                )
            )
        conn.commit()
        show_message("Данные успешно сохранены!", "success")

    except sqlite3.Error as e:
        show_message(f"Ошибка базы данных: {e}", "error")
    except Exception as e:
        show_message(f"Ошибка: {e}", "error")
        
def clear_all_entries():
    """Очищает все поля ввода."""
    surname_entry.delete(0, tk.END)
    name_entry.delete(0, tk.END)
    patronymic_entry.delete(0, tk.END)
    snils_entry.delete(0, tk.END)
    position_entry.delete(0, tk.END)
    #org_inn_entry.delete(0, tk.END)
    #org_title_entry.delete(0, tk.END)
    #employer_org_inn_entry.delete(0, tk.END)
    #employer_org_title_entry.delete(0, tk.END)                   Эти четыре строки можно добавть для того, чтобы стирались и поля организаций
    learn_program_listbox.selection_clear(0, tk.END)
    #is_passed_var.set(False)                                     Это можно добавить, чтобы при очистке снимался и чекбокс Сдано
    protocol_number_entry.delete(0, tk.END)
    exam_date_entry.delete(0, tk.END)
    isForeignSnils_var.set(False)
    foreignSnils_entry.delete(0, tk.END)
    citizenship_entry.delete(0, tk.END)

def clear_partial_entries():
    """Очищает поля Фамилия, Имя, Отчество, СНИЛС."""
    surname_entry.delete(0, tk.END)
    name_entry.delete(0, tk.END)
    patronymic_entry.delete(0, tk.END)
    snils_entry.delete(0, tk.END)
    
def create_xml(conn, target_protocol_number=None):
    """Создает XML-файл для указанного протокола или всех записей."""
    try:
        filename = f"{target_protocol_number or 'all'}_{datetime.now().strftime('%d%m%Y')}.xml"
        root = ET.Element("RegistrySet")

        with conn:
            cursor = conn.cursor()
            if target_protocol_number:
                cursor.execute("SELECT * FROM users WHERE protocol_number = ?", (target_protocol_number,))
            else:
                cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()

            for row in rows:
                record = ET.SubElement(root, "RegistryRecord")
                
                worker = ET.SubElement(record, "Worker")
                ET.SubElement(worker, "LastName").text = row[1] or ""
                ET.SubElement(worker, "FirstName").text = row[2] or ""
                ET.SubElement(worker, "MiddleName").text = row[3] or ""
                ET.SubElement(worker, "Snils").text = row[4] or ""
                ET.SubElement(worker, "IsForeignSnils").text = "true" if row[5] == 1 else "false"
                ET.SubElement(worker, "ForeignSnils").text = row[6] or ""
                ET.SubElement(worker, "Citizenship").text = row[7] or ""
                ET.SubElement(worker, "Position").text = row[8] or ""
                ET.SubElement(worker, "EmployerInn").text = row[11] or ''
                ET.SubElement(worker, "EmployerTitle").text = row[12] or ''

                organization = ET.SubElement(record, "Organization")
                ET.SubElement(organization, "Inn").text = row[9] or ""  
                ET.SubElement(organization, "Title").text = row[10] or ""  

                test = ET.SubElement(record, "Test")
                test.set("isPassed", "true" if row[14] == 1 else "false")
                test.set("learnProgramId", str(row[13]))
                
                exam_date_db = row[16]
                try:
                    exam_date_formatted = datetime.strptime(exam_date_db, '%d.%m.%Y').strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError(f"Неверный формат даты в базе данных для записи: {row[0]}. Ожидаемый формат: %d.%m.%Y")

                ET.SubElement(test, "Date").text = exam_date_formatted
                ET.SubElement(test, "ProtocolNumber").text = row[15] or ""
                try:
                    ET.SubElement(test, "LearnProgramTitle").text = program_mapping[row[13]]
                except KeyError:
                    ET.SubElement(test, "LearnProgramTitle").text = ""

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        show_message(f"XML-файл '{filename}' успешно создан!", "success")

    except ValueError as e:
        show_message(f"Ошибка: {e}", "error")
    except sqlite3.Error as e:
        show_message(f"Ошибка базы данных: {e}", "error")
    except Exception as e:
        show_message(f"Непредвиденная ошибка: {e}", "error")

def create_xml_filtered(conn):
    """Создает XML-файл для данных, соответствующих заданному номеру протокола."""
    target_protocol_number = protocol_number_for_xml_entry.get()
    if not target_protocol_number:
        show_message("Введите номер протокола для создания XML.", "error")
        return
    create_xml(conn, target_protocol_number)

def create_xml_all(conn):
    """Создает XML-файл со всеми данными из базы данных."""
    create_xml(conn)

def create_database(conn):
    """Создает базу данных (если не существует) и таблицу users."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                surname TEXT,
                name TEXT,
                patronymic TEXT,
                snils TEXT,
                isForeignSnils INTEGER,
                foreignSnils TEXT,
                citizenship TEXT,
                position TEXT,
                org_inn TEXT,
                org_title TEXT,
                employer_org_inn TEXT,
                employer_org_title TEXT,
                learn_program_id INTEGER,
                is_passed INTEGER,
                protocol_number TEXT,
                exam_date TEXT,
                entry_date TEXT
            )
            '''
        )
        conn.commit()
    except sqlite3.Error as e:
        show_message(f"Ошибка базы данных: {e}", "error")

program_mapping = {
    1: "Оказание первой помощи пострадавшим",
    2: "Использование (применение) средств индивидуальной защиты",
    3: "Общие вопросы охраны труда и функционирования системы управления охраной труда",
    4: "Безопасные методы и приемы выполнения работ при воздействии вредных и (или) опасных производственных факторов, источников опасности, идентифицированных в рамках специальной оценки условий труда и оценки профессиональных рисков",
    6: "Безопасные методы и приемы выполнения земляных работ",
    7: "Безопасные методы и приемы выполнения ремонтных, монтажных и демонтажных работ зданий и сооружений",
    8: "Безопасные методы и приемы выполнения работ при размещении, монтаже, техническом обслуживании и ремонте технологического оборудования (включая технологическое оборудование)",
    9: "Безопасные методы и приемы выполнения работ на высоте",
    10: "Безопасные методы и приемы выполнения пожароопасных работ",
    11: "Безопасные методы и приемы выполнения работ в ограниченных и замкнутых пространствах (ОЗП)",
    12: "Безопасные методы и приемы выполнения строительных работ, в том числе: - окрасочные работы - электросварочные и газосварочные работы",
    13: "Безопасные методы и приемы выполнения работ, связанные с опасностью воздействия сильнодействующих и ядовитых веществ",
    14: "Безопасные методы и приемы выполнения газоопасных работ",
    15: "Безопасные методы и приемы выполнения огневых работ",
    16: "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией подъемных сооружений",
    17: "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией тепловых энергоустановок",
    18: "Безопасные методы и приемы выполнения работ в электроустановках",
    19: "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией сосудов, работающих под избыточным давлением",
    20: "Безопасные методы и приемы обращения с животными",
    21: "Безопасные методы и приемы при выполнении водолазных работ",
    22: "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
    23: "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
    24: "Безопасные методы и приемы работ, на участках с патогенным заражением почвы",
    25: "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
    26: "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов при отсутствии машин соответствующей грузоподъемности и разборке покосившихся и опасных (неправильно уложенных) штабелей круглых лесоматериалов",
    27: "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
    28: "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
    29: "Безопасные методы и приемы работ в театрах"
}

conn = sqlite3.connect('data.db')

def show_tooltip(event, text):
    """Отображает подсказку над кнопкой."""
    widget = event.widget

    # Получаем координаты кнопки относительно окна приложения
    x = widget.winfo_x() + widget.winfo_width() // 2  # Центр кнопки по горизонтали
    y = widget.winfo_y() - tooltip_label.winfo_reqheight() - 5 # Поднимаем подсказку от кнопки на вышину окна подсказки и еще на 5

    # Устанавливаем текст подсказки
    tooltip_label.config(text=text)
    
    # Получаем размеры подсказки
    tooltip_width = tooltip_label.winfo_reqwidth()
    tooltip_height = tooltip_label.winfo_reqheight()

    # Корректируем позицию по центру кнопки
    x -= tooltip_width // 2  # Центрируем подсказку по горизонтали

    # Проверяем границы окна
    window_width = root.winfo_width()
    window_height = root.winfo_height()

    if x + tooltip_width > window_width:
        x = window_width - tooltip_width  # Не выходить за правую границу окна
    if x < 0:
        x = 0  # Не выходить за левую границу окна
    if y < 0:
        y = 0  # Не выходить за верхнюю границу окна

    # Позиционируем подсказку
    tooltip_label.place(x=x, y=y)
    tooltip_label.lift()

def hide_tooltip(event):
    """Скрывает подсказку."""
    tooltip_label.place_forget()

root = tk.Tk()                       #Запускаем окно. Настраиваем параметры окна. Цвета, шрифты, иконки...
root.configure                       #Можно задать цвет фона окна (bg="#BDBCBC")
image = PhotoImage(file="icon.png")  #Иконка в панеле задач
root.iconphoto(True, image)
root.title("Форма ввода данных")     #Надпись заголовка основного окна
root.geometry("1200x800")           #Размер окна
      
style = ttk.Style()
style.configure("TLabel", padding=(10, 5), font=("Arial", 10))
style.configure("TEntry", padding=(10, 5), font=("Arial", 10), width=60)
style.configure("TButton", padding=(10, 5), font=("Arial", 10), relief="raised", borderwidth = 1, background="#C3C3C3")
style.configure("TCheckbutton", font=("Arial", 10))

labels = ["Фамилия:", "Имя:", "Отчество:", "СНИЛС:", "Профессия:", "ИНН организации:", "Название организации:", "ИНН работодателя:", "Название работодателя:"]

entries = []

for i, label_text in enumerate(labels):
    label = ttk.Label(root, text=label_text, style="TLabel")
    label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
    entry = ttk.Entry(root, style="TEntry")
    entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
    entries.append(entry)

for i in range(len(entries)-1):
    entries[i].bind("<Return>", lambda event, idx=i: entries[idx + 1].focus())
    
def on_enter_press(event, idx):
    """Обрабатывает нажатие Enter и переводит фокус на следующее поле ввода."""
    try:
        # Проверяем, что следующее поле существует
        if idx + 1 < len(entries):
            next_entry = entries[idx + 1]
            # Проверяем, что поле видимо и доступно
            if next_entry.winfo_ismapped():
                next_entry.focus()
    except Exception as e:
        print(f"Ошибка при обработке Enter: {e}")
  
surname_entry, name_entry, patronymic_entry, snils_entry, position_entry, org_inn_entry, org_title_entry, employer_org_inn_entry, employer_org_title_entry = entries

#Задаем заранее введённые данные об организациях
org_inn_entry.insert(0, "1234567890")
org_title_entry.insert(0, "АО \"Аттестующий\"")
employer_org_inn_entry.insert(0, "0000000000")
employer_org_title_entry.insert(0, "АО \"Работодатель\"")

learn_program_label = ttk.Label(root, text="Учебные программы:", style="TLabel")
learn_program_label.grid(row=len(labels), column=0, columnspan=2, sticky="w", padx=5, pady=2)

#Настройка и расположение скроллбаров
yscrollbar = ttk.Scrollbar(root, orient="vertical")
yscrollbar.grid(row=len(labels) + 1, column=0, sticky="nse")
xscrollbar = ttk.Scrollbar(root, orient="horizontal")
xscrollbar.grid(row=len(labels), column=1, sticky="ews")

learn_program_var = tk.StringVar(value="")
learn_program_listbox = tk.Listbox(root, listvariable=learn_program_var, selectmode="multiple", width=60, height=11, selectbackground="#0079C2", selectforeground="white", exportselection=False, xscrollcommand=xscrollbar.set, yscrollcommand=yscrollbar.set)
learn_program_listbox.grid(row=len(labels)+1, column=1, sticky="ew", padx=5, pady=2)
xscrollbar.config(command=learn_program_listbox.xview)
yscrollbar.config(command=learn_program_listbox.yview)

for program_id, program_name in program_mapping.items():
    learn_program_listbox.insert(tk.END, f"{program_id}. {program_name}")

is_passed_var = tk.BooleanVar()
is_passed_var.set(True)        # Задает изначально отмеченный чекбокс Сдано
is_passed_checkbutton = ttk.Checkbutton(root, text="Сдано", variable=is_passed_var, style="TCheckbutton")
is_passed_checkbutton.grid(row=len(labels)+2, column=0, columnspan=2, sticky='w', padx=5, pady=2)

protocol_number_label = ttk.Label(root, text="Номер протокола:", style="TLabel")
protocol_number_label.grid(row=len(labels)+3, column=0, sticky="w", padx=5, pady=2)
protocol_number_entry = ttk.Entry(root, style="TEntry")
protocol_number_entry.grid(row=len(labels)+3, column=1, sticky="ew", padx=5, pady=2)
protocol_number_entry.bind("<Return>", lambda event: exam_date_entry.focus())

exam_date_label = ttk.Label(root, text="Дата проверки (дд.мм.гггг):", style="TLabel")
exam_date_label.grid(row=len(labels)+4, column=0, sticky="w", padx=5, pady=2)
exam_date_entry = ttk.Entry(root, style="TEntry")
exam_date_entry.grid(row=len(labels)+4, column=1, sticky="ew", padx=5, pady=2)

#Кнопка выбора профессии из предложенного списка (хранится в файле positions.txt)
position_button = ttk.Button(root, text="Выбрать из списка", command=lambda: show_position_options(None), style="TButton")
position_button.grid(row=4, column=2, sticky="w", padx=5, pady=2)

# Фрейм для полей "Иностранный СНИЛС" и "Гражданство"
foreign_info_frame = tk.Frame(root)

foreignSnils_label = ttk.Label(foreign_info_frame, text="Иностранный СНИЛС:", style="TLabel")
foreignSnils_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
foreignSnils_entry = ttk.Entry(foreign_info_frame, style="TEntry")
foreignSnils_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

citizenship_label = ttk.Label(foreign_info_frame, text="Гражданство:", style="TLabel")
citizenship_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
citizenship_entry = ttk.Entry(foreign_info_frame, style="TEntry")
citizenship_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

# Спойлер для полей "Иностранный СНИЛС" и "Гражданство"
isForeignSnils_var = tk.BooleanVar()
isForeignSnils_checkbutton = ttk.Checkbutton(root, text="Не гражданин РФ", variable=isForeignSnils_var, command=lambda: show_hide_foreign_info(), style="TCheckbutton")
isForeignSnils_checkbutton.grid(row=len(labels)+5, column=0, columnspan=2, sticky='w', padx=5, pady=2)

# Поле для ФИО всборе, чтобы потом заполнить отдельно первые три поля
full_name_label = ttk.Label(root, text="ФИО (введите через пробел):", style="TLabel")
full_name_label.grid(row=len(labels)+10, column=0, sticky="w", padx=5, pady=2)
full_name_entry = ttk.Entry(root, style="TEntry")
full_name_entry.grid(row=len(labels)+10, column=1, sticky="ew", padx=5, pady=2)

#Кнопка для показа лицензии
about_button = ttk.Button(root, text="О программе", command=show_license, style="TButton")
about_button.grid(row=len(labels)+10, column=2, sticky="e", padx=5, pady=2)
about_button.bind("<Enter>", lambda event: show_tooltip(event, "О программе и лицензии"))
about_button.bind("<Leave>", hide_tooltip)


def show_hide_foreign_info():
    """Показывает или скрывает поля для иностранцев."""
    if isForeignSnils_var.get():
        foreign_info_frame.grid(row=len(labels)+6, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
    else:
        foreign_info_frame.grid_remove()

foreign_info_frame.grid_remove()
    
# Создаем Label для подсказок к кнопкам
tooltip_label = tk.Label(root, text="", background="#729FCF", relief="flat", borderwidth=1, wraplength=200)
tooltip_label.place_forget()

clear_button = ttk.Button(root, text="Очистить всё", command=clear_all_entries, style="TButton")
clear_button.bind("<Enter>", lambda event: show_tooltip(event, "Очищает всё, кроме полей об организации и отметки Сдано"))
clear_button.bind("<Leave>", hide_tooltip)
clear_button.grid(row=8, column=2, sticky="w", padx=5, pady=2)

clear_partial_button = ttk.Button(root, text="Очистить (ФИО, СНИЛС)", command=clear_partial_entries, style="TButton")
clear_partial_button.bind("<Enter>", lambda event: show_tooltip(event, "Очищает только поля Фамилия, Имя, Отчество и поле СНИЛС"))
clear_partial_button.bind("<Leave>", hide_tooltip)
clear_partial_button.grid(row=3, column=2, sticky="w", padx=5, pady=2)

submit_button = ttk.Button(root, text="Отправить в БД", command=lambda: submit_data(conn), style="TButton")
submit_button.bind("<Enter>", lambda event: show_tooltip(event, "Сохраняет введенные данные в базу этой программы"))
submit_button.bind("<Leave>", hide_tooltip)
submit_button.grid(row=len(labels)+4, column=1, sticky="e", padx=5, pady=2)

protocol_number_for_xml_label = ttk.Label(root, text="Номер протокола для XML:", style="TLabel")
protocol_number_for_xml_label.grid(row=len(labels)+8, column=0, sticky="w", padx=5, pady=2)
protocol_number_for_xml_entry = ttk.Entry(root, style="TEntry")
protocol_number_for_xml_entry.grid(row=len(labels)+8, column=1, sticky="ew", padx=5, pady=2)

xml_button_filtered = ttk.Button(root, text="Создать XML (для протокола)", command=lambda: create_xml_filtered(conn), style="TButton")
xml_button_filtered.bind("<Enter>", lambda event: show_tooltip(event, "Создаёт в папке с программой файл XML только для одного определённого протокола"))
xml_button_filtered.bind("<Leave>", hide_tooltip)
xml_button_filtered.grid(row=len(labels)+8, column=2, sticky="w", padx=5, pady=2)

xml_button_all = ttk.Button(root, text="Создать XML (вся база)", command=lambda: create_xml_all(conn), style="TButton")
xml_button_all.bind("<Enter>", lambda event: show_tooltip(event, "Создаёт в папке с программой файл XML для всех протоколов, сохраненных в базу данных этой программы"))
xml_button_all.bind("<Leave>", hide_tooltip)
xml_button_all.grid(row=len(labels)+9, column=2, sticky="w", padx=5, pady=2)

def delete_protocol_entry(conn, tree):
    """Удаляет выбранные записи из базы данных и обновляет Treeview."""
    try:
        selected_items = tree.selection()
        if not selected_items:
            show_message("Выберите записи для удаления.", "error")
            return

        ids_to_delete = [tree.item(item)['values'][-1] for item in selected_items]

        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить выбранные записи?"):
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id IN ({})".format(','.join(['?'] * len(ids_to_delete))), ids_to_delete)
                rows_affected = cursor.rowcount

            if rows_affected > 0:
                for item in selected_items:
                    tree.delete(item)
                show_message(f"Выбранные записи успешно удалены!", "success")
            else:
                show_message(f"Ошибка удаления выбранных записей.", "error")

    except sqlite3.Error as e:
        messagebox.showerror("Ошибка", f"Ошибка базы данных: {e}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка: {e}")

def show_details(conn, tree, selected_item):
    """Отображает подробную информацию о выбранном протоколе."""
    try:
        item_id = tree.item(selected_item)['values'][-1]  # Получаем ID из treeview

        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            global column_names
            column_names = [description[0] for description in cursor.description]  # Сохраняем имена столбцов

            detail_window = tk.Toplevel(root)
            detail_window.title("Подробная информация")

            global entries, initial_values
            entries = []
            initial_values = row  # Сохраняем начальные значения для сравнения

            # Создание меток и полей ввода для редактирования
            for i, value in enumerate(row):
                label = ttk.Label(detail_window, text=column_names[i], anchor="w")
                label.grid(row=i, column=0, sticky="w")
                
                entry = ttk.Entry(detail_window)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky="ew")
                entries.append(entry)

                # Привязываем обработчик Enter только для текущего окна
                entry.bind("<Return>", lambda event, idx=i: on_detail_enter(event, idx, entries))

            # Кнопка для сохранения изменений
            save_button = ttk.Button(detail_window, text="Сохранить изменения", command=lambda: save_changes(item_id))
            save_button.grid(row=len(row), column=1)

            # Обработчик закрытия окна
            def on_detail_window_close():
                # Отвязываем все обработчики событий
                for entry in entries:
                    entry.unbind("<Return>")
                detail_window.destroy()

            detail_window.protocol("WM_DELETE_WINDOW", on_detail_window_close)
            
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка: {e}")

def on_detail_enter(event, idx, entries):
    """Обрабатывает нажатие Enter в окне подробной информации."""
    try:
        if idx + 1 < len(entries):
            next_entry = entries[idx + 1]
            if next_entry.winfo_exists():  # Проверяем, существует ли виджет
                next_entry.focus()
    except Exception as e:
        print(f"Ошибка при обработке Enter: {e}")
        
def save_changes(item_id):
    """Сохраняет изменения в базе данных."""
    try:
        updated_values = []
        set_clause = []
        
        current_values = [entry.get() for entry in entries]

        for i, value in enumerate(current_values):
            if value != initial_values[i]:  # Если значение изменено
                set_clause.append(f"{column_names[i]}=?")
                updated_values.append(value)

        # Добавляем id в конец
        if set_clause:
            updated_values.append(item_id)
            query = f"""
                UPDATE users SET {', '.join(set_clause)} WHERE id=?
            """
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, updated_values)
            show_message("Изменения успешно сохранены!", "success")
        else:
            show_message("Нет изменений для сохранения.", "info")

    except sqlite3.Error as e:
        show_message(f"Ошибка базы данных: {e}", "error")
    except Exception as e:
        show_message(f"Ошибка: {e}", "error")

def show_protocol_info(conn):
    """Отображает информацию о протоколах в Treeview с сортировкой и прокруткой."""
    try:
        protocol_info_window = tk.Toplevel(root)
        protocol_info_window.title("Информация о протоколах")
        protocol_info_window.geometry("1500x800")

        # Фрейм для Treeview и прокрутки
        tree_frame = ttk.Frame(protocol_info_window)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=2)

        # Горизонтальная и вертикальная прокрутка
        yscrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        xscrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Настройка Treeview
        tree = ttk.Treeview(
            tree_frame,
            columns=("Протокол", "Фамилия", "Имя", "Отчество", "Дата", "Программа", "ID"),
            show="headings",
            yscrollcommand=yscrollbar.set,
            xscrollcommand=xscrollbar.set,
            selectmode="extended"
        )

        yscrollbar.config(command=tree.yview)
        xscrollbar.config(command=tree.xview)

        # Заголовки колонок
        tree.heading("Протокол", text="Протокол", anchor="w")
        tree.heading("Фамилия", text="Фамилия", anchor="w")
        tree.heading("Имя", text="Имя", anchor="w")
        tree.heading("Отчество", text="Отчество", anchor="w")
        tree.heading("Дата", text="Дата проверки", anchor="w")
        tree.heading("Программа", text="Учебная программа", anchor="w")
        tree.heading("ID", text="ID", anchor="w")

        # Ширина колонок
        tree.column("Протокол", width=70, stretch=False)
        tree.column("Фамилия", width=150, stretch=False)
        tree.column("Имя", width=150, stretch=False)
        tree.column("Отчество", width=150, stretch=False)
        tree.column("Дата", width=100, stretch=False)
        tree.column("Программа", width=530, stretch=False)
        tree.column("ID", width=0, stretch=False, minwidth=0)  # Скрытая колонка

        # Размещение Treeview и прокрутки
        tree.pack(side="left", fill="both", expand=True)
        yscrollbar.pack(side="right", fill="y")
        xscrollbar.pack(side="bottom", fill="x")

        # Функция сортировки
        def treeview_sort_column(col, reverse):
            data = [(tree.set(child, col), child) for child in tree.get_children('')]
            data.sort(reverse=reverse)
            for index, (val, child) in enumerate(data):
                tree.move(child, '', index)
            tree.heading(col, command=lambda: treeview_sort_column(col, not reverse))

        # Настройка сортировки для всех колонок
        for col in ("Протокол", "Фамилия", "Имя", "Отчество", "Дата", "Программа"):
            tree.heading(col, command=lambda c=col: treeview_sort_column(c, False))

        # Загрузка данных
        def load_data():
            tree.delete(*tree.get_children())
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        protocol_number, 
                        surname, 
                        name, 
                        patronymic, 
                        exam_date, 
                        learn_program_id,
                        id
                    FROM users
                    ORDER BY protocol_number
                """)
                rows = cursor.fetchall()
                for row in rows:
                    # Получаем название программы из словаря program_mapping
                    program_id = row[5]
                    program_name = program_mapping.get(program_id, "Неизвестная программа")
                    # Вставляем данные в Treeview
                    tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], program_name, row[6]))

        load_data()

        # Контекстное меню
        context_menu = tk.Menu(protocol_info_window, tearoff=0)
        context_menu.add_command(
            label="Сформировать XML",
            command=lambda: generate_xml_for_selected(conn, tree)
        )
        context_menu.add_command(
            label="Удалить запись",
            command=lambda: delete_selected_entry(conn, tree)
        )
        context_menu.add_command(
            label="Просмотр и изменение",
            command=lambda: show_details(conn, tree, tree.selection()[0])
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Обновить данные",
            command=load_data
        )

        # Обработчики событий
        def on_right_click(event):
            try:
                selected_item = tree.identify_row(event.y)
                if selected_item:
                    tree.selection_set(selected_item)
                    context_menu.post(event.x_root, event.y_root)
            except Exception as e:
                print(f"Ошибка контекстного меню: {e}")

        def on_double_click(event):
            try:
                selected_item = tree.identify_row(event.y)
                if selected_item:
                    tree.selection_set(selected_item)
                    show_details(conn, tree, selected_item)
            except Exception as e:
                print(f"Ошибка двойного клика: {e}")

        tree.bind("<Button-3>", on_right_click)
        tree.bind("<Double-1>", on_double_click)

        # Статусная строка
        status_frame = ttk.Frame(protocol_info_window)
        status_frame.pack(fill="x", padx=5, pady=2)
        
        status_label = ttk.Label(
            status_frame,
            text=f"Всего записей: {len(tree.get_children())}",
            relief="sunken"
        )
        status_label.pack(side="left", fill="x", expand=True)

        # Функция обновления статусной строки
        def update_status():
            status_label.config(text=f"Всего записей: {len(tree.get_children())}")
            protocol_info_window.after(1000, update_status)

        update_status()

        protocol_info_window.mainloop()

    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка: {e}")
        
def generate_xml_for_selected(conn, tree):
    """Генерирует XML для выбранного протокола."""
    try:
        selected_item = tree.selection()[0]
        protocol_number = tree.item(selected_item, 'values')[0]
        if protocol_number:
            create_xml(conn, protocol_number)
        else:
            show_message("Не выбран протокол.", "error")
    except IndexError:
        show_message("Не выбрана запись.", "error")
    except Exception as e:
        show_message(f"Ошибка генерации XML: {e}", "error")

def delete_selected_entry(conn, tree):
    """Удаляет выбранную запись, запрашивая подтверждение."""
    selected_items = tree.selection()
    if not selected_items:
        show_message("Выберите запись для удаления.", "error")
        return

    ids_to_delete = [tree.item(item)['values'][-1] for item in selected_items]
    if messagebox.askyesno("Подтверждение удаления", f"Уверены, что хотите удалить {len(ids_to_delete)} запись(и)?"):
        delete_protocol_entry(conn, tree)        

#Привязка проверки к событию потери фокуса на поле "Отчество"
def on_patronymic_focus_out(event):
    surname = surname_entry.get()
    name = name_entry.get()
    patronymic = patronymic_entry.get()

    if surname and name and patronymic:
        suggest_autofill_data(conn, surname, name, patronymic)

patronymic_entry.bind("<FocusOut>", on_patronymic_focus_out)

protocol_info_button = ttk.Button(root, text="Информация о протоколах", command=lambda: show_protocol_info(conn), style="TButton")
protocol_info_button.bind("<Enter>", lambda event: show_tooltip(event, "Выводит окно с краткой информацией о сохранённых в базу данных программы записях"))
protocol_info_button.bind("<Leave>", hide_tooltip)
protocol_info_button.grid(row=len(labels)+4, column=2,  sticky="w", padx=5, pady=2)

def on_date_enter_press(event):
    """Обрабатывает нажатие Enter на поле "Дата проверки" и переводит фокус на следующее поле или кнопку."""
    widget = event.widget
    if widget == exam_date_entry:
        submit_button.focus()
    elif widget == submit_button:
        submit_button.invoke()
exam_date_entry.bind("<Return>", on_date_enter_press)
submit_button.bind("<Return>", on_date_enter_press)

# Функция для обработки события нажатия Enter
def on_full_name_enter(event):
    full_name = full_name_entry.get().strip()  # Убираем лишние пробелы
    parts = full_name.split()  # Разделяем строку по пробелам
    
    if len(parts) == 3:
        # Заполняем поля "Фамилия", "Имя" и "Отчество"
        surname_entry.delete(0, tk.END)
        surname_entry.insert(0, parts[0])
        
        name_entry.delete(0, tk.END)
        name_entry.insert(0, parts[1])
        
        patronymic_entry.delete(0, tk.END)
        patronymic_entry.insert(0, parts[2])
        
        # Устанавливаем фокус на поле "Отчество"
        patronymic_entry.focus()
    else:
        # Если введено не три слова, показываем сообщение об ошибке
        show_message("Ошибка: введите Фамилию, Имя и Отчество через пробел (три слова).", "error")

full_name_entry.bind("<Return>", on_full_name_enter)

def on_arrow_press(event):
    """Обрабатывает нажатие стрелок и перемещает курсор в соответствующее поле."""
    current_entry = event.widget
    current_cursor_index = current_entry.index(tk.INSERT)  # Получаем позицию курсора

    if event.keysym == "Up":
        new_row = current_entry.grid_info()["row"] - 1
    elif event.keysym == "Down":
        new_row = current_entry.grid_info()["row"] + 1
    elif event.keysym == "Left":
        current_entry.icursor(current_cursor_index - 1)
        return  # Не переключаем поле, если стрелка влево
    elif event.keysym == "Right":
        current_entry.icursor(current_cursor_index + 1)
        return  # Не переключаем поле, если стрелка вправо
    else:
        return

    new_col = current_entry.grid_info()["column"]

    try:
        next_entry = root.grid_slaves(row=new_row, column=new_col)[0]
        if isinstance(next_entry, tk.Entry) or isinstance(next_entry, ttk.Entry):
            next_entry.focus()
            next_entry.icursor(tk.END)  # Устанавливаем курсор в конец поля
    except IndexError:
        pass

# Привязываем обработчик к событиям нажатия стрелок
for entry in entries:
    entry.bind("<Up>", on_arrow_press)
    entry.bind("<Down>", on_arrow_press)
    entry.bind("<Left>", on_arrow_press)
    entry.bind("<Right>", on_arrow_press) 


create_database(conn)

root.columnconfigure(1, weight=1)
root.mainloop()
conn.close()

