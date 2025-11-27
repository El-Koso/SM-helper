## Лицензия. Этот проект распространяется под лицензией GPLv3.
## Подробности можно найти в файле COPYING

import sys
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QCheckBox, QScrollArea, QDialog, QCalendarWidget, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QIcon

PROGRAM_MAPPING = {
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

program_mapping = PROGRAM_MAPPING


def validate_snils(snils):
    if not re.match(r"^\d{3}-\d{3}-\d{3} \d{2}$", snils) and not re.match(r"^\d{11}$", snils):
        return False

    snils_clean = re.sub(r"[^\d]", "", snils)
    if len(snils_clean) != 11:
        return False

    main_part = snils_clean[:9]
    control_sum = int(snils_clean[-2:])

    total = 0
    for i, digit in enumerate(main_part, start=1):
        total += int(digit) * (10 - i)

    if total < 100:
        return total == control_sum
    elif total == 100 or total == 101:
        return control_sum == 0
    else:
        remainder = total % 101
        if remainder == 100:
            return control_sum == 0
        else:
            return remainder == control_sum


def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False


class InstructionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Инструкция")
        self.setMinimumSize(1200, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.text_label)
        layout.addWidget(scroll)

        try:
            with open("manual.txt", "r", encoding="utf-8") as file:
                license_text = file.read()
            self.text_label.setText(license_text)
        except FileNotFoundError:
            self.text_label.setText("Файл инструкции не найден!")
        except Exception as e:
            self.text_label.setText(f"Ошибка при чтении файла инструкции: {e}")


class PositionSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите должность")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        try:
            with open("positions.txt", "r", encoding="utf-8") as file:
                positions = [pos.strip() for pos in file.readlines()]
            for pos in positions:
                if pos:
                    self.list_widget.addItem(pos)
        except FileNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Файл positions.txt не найден.")
            self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
            self.reject()

        self.list_widget.itemDoubleClicked.connect(self.item_selected)

        self.selected_position = None

    def item_selected(self, item):
        self.selected_position = item.text()
        self.accept()

    @staticmethod
    def get_position(parent=None):
        dialog = PositionSelectorDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.selected_position
        return None


class OrganizationSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите организацию")
        self.setMinimumSize(800, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        try:
            with open("organizations.txt", "r", encoding="utf-8") as file:
                organizations = [org.strip() for org in file.readlines() if org.strip()]
            for org in organizations:
                if org:
                    self.list_widget.addItem(org)
        except FileNotFoundError:
            QMessageBox.critical(self, "Ошибка", "Файл organizations.txt не найден.")
            self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
            self.reject()

        self.list_widget.itemDoubleClicked.connect(self.item_selected)

        self.selected_organization = None
        self.selected_inn = None

    def item_selected(self, item):
        full_text = item.text()
        # Разделяем по точке с запятой
        parts = full_text.split(';', 1)
        if len(parts) == 2:
            self.selected_inn = parts[0].strip()
            self.selected_organization = parts[1].strip()
        else:
            # Если формат неверный, используем весь текст как название
            self.selected_organization = full_text
            self.selected_inn = ""
        self.accept()

    @staticmethod
    def get_organization(parent=None):
        dialog = OrganizationSelectorDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.selected_inn, dialog.selected_organization
        return None, None


class CalendarDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите дату")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.activated.connect(self.accept)
        
        layout.addWidget(self.calendar)

        button_box = QHBoxLayout()
        layout.addLayout(button_box)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_box.addWidget(ok_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)

    def get_selected_date(self):
        return self.calendar.selectedDate()


class ProtocolDetailsDialog(QDialog):
    def __init__(self, conn, record_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подробная информация")
        self.setMinimumSize(600, 700)
        self.conn = conn
        self.record_id = record_id
        self.entries = []
        self.column_names = []
        self.initial_values = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        form_layout = QGridLayout()
        layout.addLayout(form_layout)

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена в базе данных.")
            self.reject()
            return

        self.initial_values = row
        self.column_names = [desc[0] for desc in cursor.description]

        for i, value in enumerate(row):
            label = QLabel(self.column_names[i])
            form_layout.addWidget(label, i, 0)

            line_edit = QLineEdit()
            line_edit.setText(str(value) if value is not None else "")
            form_layout.addWidget(line_edit, i, 1)
            self.entries.append(line_edit)

            def make_on_return(idx):
                def on_return():
                    if idx + 1 < len(self.entries):
                        self.entries[idx + 1].setFocus()
                return on_return

            line_edit.returnPressed.connect(make_on_return(i))

        self.save_button = QPushButton("Сохранить изменения")
        self.save_button.clicked.connect(self.save_changes)
        layout.addWidget(self.save_button)

    def save_changes(self):
        updated_values = []
        set_clause = []

        current_values = [e.text() for e in self.entries]

        for i, value in enumerate(current_values):
            if value != (self.initial_values[i] if self.initial_values[i] is not None else ""):
                set_clause.append(f"{self.column_names[i]}=?")
                updated_values.append(value)

        if not set_clause:
            QMessageBox.information(self, "Информация", "Нет изменений для сохранения.")
            return

        updated_values.append(self.record_id)
        query = f"UPDATE users SET {', '.join(set_clause)} WHERE id=?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, updated_values)
            self.conn.commit()
            QMessageBox.information(self, "Успех", "Изменения успешно сохранены!")
            self.accept()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


class ProtocolInfoDialog(QDialog):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Информация о протоколах")
        self.setMinimumSize(1500, 800)
        self.conn = conn

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Дерево протоколов: множественный выбор по Ctrl, группы свернуты по умолчанию
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Протокол", "Фамилия", "Имя", "Отчество", "Дата проверки", "Учебная программа"])
        self.tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_widget.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree_widget.setSortingEnabled(False)
        layout.addWidget(self.tree_widget)

        buttons_layout = QHBoxLayout()
        layout.addLayout(buttons_layout)

        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.clicked.connect(self.load_data)
        buttons_layout.addWidget(self.refresh_btn)

        self.xml_btn = QPushButton("Сформировать XML (по записи)")
        self.xml_btn.clicked.connect(self.generate_xml_for_selected)
        buttons_layout.addWidget(self.xml_btn)

        self.xml_selected_protocols_btn = QPushButton("Создать XML (выбранные протоколы)")
        self.xml_selected_protocols_btn.clicked.connect(self.generate_xml_for_selected_protocols)
        buttons_layout.addWidget(self.xml_selected_protocols_btn)

        self.delete_btn = QPushButton("Удалить запись")
        self.delete_btn.clicked.connect(self.delete_selected_entry)
        buttons_layout.addWidget(self.delete_btn)

        self.details_btn = QPushButton("Просмотр и изменение")
        self.details_btn.clicked.connect(self.show_details)
        buttons_layout.addWidget(self.details_btn)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.open_context_menu)

        self.load_data()

    def load_data(self):
        self.tree_widget.setSortingEnabled(False)
        self.tree_widget.clear()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT protocol_number, surname, name, patronymic, exam_date, learn_program_id, id
            FROM users
            ORDER BY protocol_number, surname, name
        """)
        rows = cursor.fetchall()

        current_protocol_item = None
        current_protocol_number = None

        for row_data in rows:
            protocol_number = row_data[0] or ""
            if current_protocol_item is None or str(current_protocol_number) != str(protocol_number):
                current_protocol_number = protocol_number
                current_protocol_item = QTreeWidgetItem(self.tree_widget, [str(protocol_number), "", "", "", "", ""])
                # По умолчанию свернуто
                current_protocol_item.setExpanded(False)

            program_name = program_mapping.get(row_data[5], "Неизвестная программа")

            child_item = QTreeWidgetItem(current_protocol_item, [
                "",  # Протокол у родителя
                str(row_data[1] or ""),
                str(row_data[2] or ""),
                str(row_data[3] or ""),
                str(row_data[4] or ""),
                program_name
            ])
            child_item.setData(0, Qt.UserRole, row_data[6])

        total_records = len(rows)
        self.status_label.setText(f"Всего записей: {total_records}")

        # Гарантированно свернуть все группы
        self.tree_widget.collapseAll()
        self.tree_widget.setSortingEnabled(False)

    def get_selected_row_id(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Внимание", "Выберите запись.")
            return None

        selected_item = selected_items[0]
        if selected_item.parent() is None:
            if selected_item.childCount() > 0:
                return selected_item.child(0).data(0, Qt.UserRole)
            else:
                QMessageBox.warning(self, "Внимание", "Выберите конкретную запись, а не номер протокола.")
                return None
        return selected_item.data(0, Qt.UserRole)

    def get_selected_protocol_numbers(self):
        selected_items = self.tree_widget.selectedItems()
        seen = set()
        protocols = []
        for item in selected_items:
            if item.parent() is None:
                proto = item.text(0).strip()
            else:
                proto = item.parent().text(0).strip()
            if proto and proto not in seen:
                seen.add(proto)
                protocols.append(proto)
        # Естественная сортировка: числовая, если все цифры, иначе строковая
        if all(p.isdigit() for p in protocols):
            protocols.sort(key=lambda x: int(x))
        else:
            protocols.sort()
        return protocols

    def generate_xml_for_selected(self):
        record_id = self.get_selected_row_id()
        if record_id is None:
            return
        cursor = self.conn.cursor()
        cursor.execute("SELECT protocol_number FROM users WHERE id=?", (record_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            QMessageBox.warning(self, "Ошибка", "Протокол у выбранной записи отсутствует.")
            return
        create_xml(self.conn, row[0])
        QMessageBox.information(self, "Успех", "XML-файл успешно создан.")

    def generate_xml_for_selected_protocols(self):
        protocols = self.get_selected_protocol_numbers()
        if not protocols:
            QMessageBox.warning(self, "Ошибка", "Выделите хотя бы один протокол (можно удерживая Ctrl).")
            return
        try:
            create_xml_for_protocols(self.conn, protocols)
            QMessageBox.information(self, "Успех", f"XML для выбранных протоколов ({len(protocols)}) успешно создан.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_selected_entry(self):
        record_id = self.get_selected_row_id()
        if record_id is None:
            return
        reply = QMessageBox.question(
            self, "Подтверждение", f"Вы уверены, что хотите удалить запись с ID {record_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (record_id,))
                self.conn.commit()
                QMessageBox.information(self, "Успех", "Запись успешно удалена!")
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", str(e))

    def show_details(self):
        record_id = self.get_selected_row_id()
        if record_id is None:
            return
        detail_dialog = ProtocolDetailsDialog(self.conn, record_id, self)
        detail_dialog.exec_()
        self.load_data()

    def open_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Сформировать XML (по записи)", self.generate_xml_for_selected)
        menu.addAction("Создать XML по выбранным протоколам", self.generate_xml_for_selected_protocols)
        menu.addAction("Удалить запись", self.delete_selected_entry)
        menu.addAction("Просмотр и изменение", self.show_details)
        menu.exec_(self.tree_widget.viewport().mapToGlobal(position))


def get_user_data_from_db(conn, surname, name, patronymic):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT snils, position FROM users WHERE surname = ? AND name = ? AND patronymic = ?", (surname, name, patronymic))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None
    except sqlite3.Error as e:
        QMessageBox.critical(None, "Ошибка базы данных", f"Ошибка: {e}")
        return None, None


def suggest_autofill_data(parent, conn, surname, name, patronymic, snils_edit, position_edit):
    snils, position = get_user_data_from_db(conn, surname, name, patronymic)
    if snils or position:
        reply = QMessageBox.question(
            parent,
            "Автозаполнение данных",
            f"Найдена запись с такой же фамилией, именем и отчеством.\n"
            f"СНИЛС: {snils}\n"
            f"Профессия: {position}\n\n"
            "Заполнить поля СНИЛС и Профессия автоматически?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if snils:
                snils_edit.setText(snils)
            if position:
                position_edit.setText(position)


def _emit_xml_records_from_rows(root, rows):
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


def create_xml(conn, target_protocol_number=None):
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

            _emit_xml_records_from_rows(root, rows)

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
    except ValueError as e:
        QMessageBox.critical(None, "Ошибка", str(e))
    except sqlite3.Error as e:
        QMessageBox.critical(None, "Ошибка базы данных", str(e))
    except Exception as e:
        QMessageBox.critical(None, "Непредвиденная ошибка", str(e))


def create_xml_for_protocols(conn, protocols):
    """
    Создает единый XML-файл для списка выбранных протоколов.
    Имя файла: "<proto1,proto2,...>_<ddMMyyyy>.xml", например "581,565,454_02092025.xml"
    """
    if not protocols:
        raise ValueError("Список протоколов пуст.")

    # Имя файла: номера через запятую (без пробелов) + дата
    date_str = datetime.now().strftime('%d%m%Y')
    proto_part = ",".join(protocols)
    filename = f"{proto_part}_{date_str}.xml"

    try:
        root = ET.Element("RegistrySet")

        placeholders = ",".join(["?"] * len(protocols))
        query = f"""
            SELECT * FROM users 
            WHERE protocol_number IN ({placeholders}) 
            ORDER BY protocol_number, surname, name
        """
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, protocols)
            rows = cursor.fetchall()
            if not rows:
                raise ValueError("В базе данных нет записей для выбранных протоколов.")

            _emit_xml_records_from_rows(root, rows)

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
    except ValueError as e:
        QMessageBox.critical(None, "Ошибка", str(e))
        raise
    except sqlite3.Error as e:
        QMessageBox.critical(None, "Ошибка базы данных", str(e))
        raise
    except Exception as e:
        QMessageBox.critical(None, "Непредвиденная ошибка", str(e))
        raise


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.conn = sqlite3.connect('data.db')
        self.create_database()

        self.setWindowTitle("Форма ввода данных")
        self.setWindowIcon(QIcon("icon.png"))
        self.setMinimumSize(1215, 850)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QGridLayout()
        central_widget.setLayout(self.main_layout)

        labels_text = [
            "Фамилия:", "Имя:", "Отчество:", "СНИЛС:", "Профессия:",
            "ИНН организации:", "Название организации:",
            "ИНН работодателя:", "Название работодателя:"
        ]

        self.entries = []
        for i, text in enumerate(labels_text):
            label = QLabel(text)
            entry = QLineEdit()
            self.main_layout.addWidget(label, i, 0)
            self.main_layout.addWidget(entry, i, 1)
            self.entries.append(entry)

        (
            self.surname_entry, self.name_entry, self.patronymic_entry, self.snils_entry,
            self.position_entry, self.org_inn_entry, self.org_title_entry,
            self.employer_org_inn_entry, self.employer_org_title_entry
        ) = self.entries

        # Установка значений по умолчанию
        self.org_inn_entry.setText("введите ИНН аттестовывающей организации")
        self.org_title_entry.setText("введите название аттестовывающей организации")
        self.employer_org_inn_entry.setText("введите ИНН работодателя")
        self.employer_org_title_entry.setText("введите название работодателя")

        for i in range(len(self.entries) - 1):
            self.entries[i].returnPressed.connect(self._make_focus_next_func(i))

        self.position_button = QPushButton("Выбрать из списка")
        self.position_button.clicked.connect(self.select_position)
        self.main_layout.addWidget(self.position_button, 4, 2)

        # Кнопки выбора организаций
        self.org_select_button = QPushButton("Выбрать организацию")
        self.org_select_button.clicked.connect(self.select_organization)
        self.main_layout.addWidget(self.org_select_button, 6, 2)

        self.employer_select_button = QPushButton("Выбрать работодателя")
        self.employer_select_button.clicked.connect(self.select_employer)
        self.main_layout.addWidget(self.employer_select_button, 8, 2)

        learn_program_label = QLabel("Учебные программы:")
        self.main_layout.addWidget(learn_program_label, 9, 0, 1, 2, Qt.AlignLeft)

        self.learn_program_list = QListWidget()
        self.learn_program_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.learn_program_list.setMinimumHeight(220)
        for program_id, program_name in program_mapping.items():
            item = QListWidgetItem(f"{program_id}. {program_name}")
            item.setData(Qt.UserRole, program_id)
            self.learn_program_list.addItem(item)
        self.learn_program_list.itemSelectionChanged.connect(self.update_selected_count)
        self.main_layout.addWidget(self.learn_program_list, 10, 0, 1, 2)
        
        self.selected_count_label = QLabel("Выбрано: 0")
        self.main_layout.addWidget(self.selected_count_label, 10, 2, Qt.AlignTop)

        self.is_passed_checkbox = QCheckBox("Сдано")
        self.is_passed_checkbox.setChecked(True)
        self.main_layout.addWidget(self.is_passed_checkbox, 11, 0, 1, 2, Qt.AlignLeft)

        protocol_number_label = QLabel("Номер протокола:")
        self.protocol_number_entry = QLineEdit()
        self.protocol_number_entry.returnPressed.connect(lambda: self.exam_date_entry.setFocus())
        self.main_layout.addWidget(protocol_number_label, 12, 0)
        self.main_layout.addWidget(self.protocol_number_entry, 12, 1)

        exam_date_label = QLabel("Дата аттестации:")
        self.exam_date_entry = QLineEdit()
        self.main_layout.addWidget(exam_date_label, 13, 0)
        self.main_layout.addWidget(self.exam_date_entry, 13, 1)

        self.calendar_button = QPushButton("Выбрать дату")
        self.calendar_button.clicked.connect(self.show_calendar)
        self.main_layout.addWidget(self.calendar_button, 13, 2)

        self.submit_button = QPushButton("Отправить в БД")
        self.submit_button.clicked.connect(self.submit_data)
        self.main_layout.addWidget(self.submit_button, 14, 1, Qt.AlignRight)

        self.protocol_info_button = QPushButton("Информация о протоколах")
        self.protocol_info_button.clicked.connect(self.show_protocol_info)
        self.main_layout.addWidget(self.protocol_info_button, 14, 2, Qt.AlignLeft)

        self.isForeignSnils_checkbox = QCheckBox("Не гражданин РФ")
        self.isForeignSnils_checkbox.stateChanged.connect(self.toggle_foreign_info)
        self.main_layout.addWidget(self.isForeignSnils_checkbox, 15, 0, 1, 2)

        self.foreign_info_widget = QWidget()
        foreign_layout = QGridLayout()
        self.foreign_info_widget.setLayout(foreign_layout)

        foreignSnils_label = QLabel("Иностранный СНИЛС:")
        self.foreignSnils_entry = QLineEdit()
        citizenship_label = QLabel("Гражданство:")
        self.citizenship_entry = QLineEdit()

        foreign_layout.addWidget(foreignSnils_label, 0, 0)
        foreign_layout.addWidget(self.foreignSnils_entry, 0, 1)
        foreign_layout.addWidget(citizenship_label, 1, 0)
        foreign_layout.addWidget(self.citizenship_entry, 1, 1)

        self.main_layout.addWidget(self.foreign_info_widget, 16, 0, 1, 3)
        self.foreign_info_widget.hide()

        full_name_label = QLabel("ФИО (введите через пробел):")
        self.full_name_entry = QLineEdit()
        self.full_name_entry.returnPressed.connect(self.parse_full_name)
        self.main_layout.addWidget(full_name_label, 20, 0)
        self.main_layout.addWidget(self.full_name_entry, 20, 1)

        self.manual_button = QPushButton("Инструкция")
        self.manual_button.clicked.connect(self.show_manual)
        self.main_layout.addWidget(self.manual_button, 20, 2)

        # Перемещаем кнопки очистки ниже
        self.clear_all_button = QPushButton("Очистить всё")
        self.clear_all_button.clicked.connect(self.clear_all_entries)
        self.main_layout.addWidget(self.clear_all_button, 17, 2)

        self.clear_partial_button = QPushButton("Очистить (ФИО, СНИЛС)")
        self.clear_partial_button.clicked.connect(self.clear_partial_entries)
        self.main_layout.addWidget(self.clear_partial_button, 3, 2)

        protocol_xml_label = QLabel("Номер протокола для XML:")
        self.protocol_number_for_xml_entry = QLineEdit()
        self.xml_button_filtered = QPushButton("Создать XML (для протокола)")
        self.xml_button_filtered.clicked.connect(self.create_xml_filtered)

        self.xml_button_all = QPushButton("Создать XML (вся база)")
        self.xml_button_all.clicked.connect(self.create_xml_all)

        row_base = 18
        self.main_layout.addWidget(protocol_xml_label, row_base, 0)
        self.main_layout.addWidget(self.protocol_number_for_xml_entry, row_base, 1)
        self.main_layout.addWidget(self.xml_button_filtered, row_base, 2)
        self.main_layout.addWidget(self.xml_button_all, row_base + 1, 2)

        self.exam_date_entry.returnPressed.connect(lambda: self.submit_button.setFocus())
        self.submit_button.setAutoDefault(True)
        self.submit_button.pressed.connect(self.submit_data)

        self.patronymic_entry.editingFinished.connect(self.try_autocomplete_snils_and_position)

        for edit in self.entries:
            edit.keyPressEvent = self._make_arrow_navigation(edit.keyPressEvent, edit)

    def _make_focus_next_func(self, index):
        def func():
            if index + 1 < len(self.entries):
                next_widget = self.entries[index + 1]
                next_widget.setFocus()
        return func

    def _make_arrow_navigation(self, original_handler, widget):
        def new_handler(event):
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down):
                row = self.main_layout.getItemPosition(self.main_layout.indexOf(widget))[0]
                col = self.main_layout.getItemPosition(self.main_layout.indexOf(widget))[1]
                if key == Qt.Key_Up:
                    new_row = row - 1
                else:
                    new_row = row + 1
                if new_row >= 0:
                    items = self._get_widgets_by_position(new_row, col)
                    if items:
                        items[0].setFocus()
                        items[0].setCursorPosition(len(items[0].text()))
                return
            if key == Qt.Key_Left:
                cursor_pos = widget.cursorPosition()
                if cursor_pos > 0:
                    original_handler(event)
                    return
            if key == Qt.Key_Right:
                cursor_pos = widget.cursorPosition()
                if cursor_pos < len(widget.text()):
                    original_handler(event)
                    return
            original_handler(event)
        return new_handler

    def _get_widgets_by_position(self, row, column):
        widgets = []
        for i in range(self.main_layout.count()):
            r, c, _, _ = self.main_layout.getItemPosition(i)
            if r == row and c == column:
                item = self.main_layout.itemAt(i)
                if item.widget():
                    widgets.append(item.widget())
        return widgets

    def toggle_foreign_info(self, state):
        if self.isForeignSnils_checkbox.isChecked():
            self.foreign_info_widget.show()
        else:
            self.foreign_info_widget.hide()

    def select_position(self):
        pos = PositionSelectorDialog.get_position(self)
        if pos:
            self.position_entry.setText(pos)

    def select_organization(self):
        inn, title = OrganizationSelectorDialog.get_organization(self)
        if inn and title:
            self.org_inn_entry.setText(inn)
            self.org_title_entry.setText(title)

    def select_employer(self):
        inn, title = OrganizationSelectorDialog.get_organization(self)
        if inn and title:
            self.employer_org_inn_entry.setText(inn)
            self.employer_org_title_entry.setText(title)

    def show_manual(self):
        dialog = InstructionDialog(self)
        dialog.exec_()

    def show_calendar(self):
        dialog = CalendarDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            date = dialog.get_selected_date()
            self.exam_date_entry.setText(date.toString("dd.MM.yyyy"))

    def update_selected_count(self):
        count = len(self.learn_program_list.selectedItems())
        self.selected_count_label.setText(f"Выбрано: {count}")

    def clear_all_entries(self):
        self.surname_entry.clear()
        self.name_entry.clear()
        self.patronymic_entry.clear()
        self.snils_entry.clear()
        self.position_entry.clear()
        self.org_inn_entry.clear()
        self.org_title_entry.clear()
        self.employer_org_inn_entry.clear()
        self.employer_org_title_entry.clear()
        self.learn_program_list.clearSelection()
        self.is_passed_checkbox.setChecked(True)
        self.protocol_number_entry.clear()
        self.exam_date_entry.clear()
        self.isForeignSnils_checkbox.setChecked(False)
        self.foreignSnils_entry.clear()
        self.citizenship_entry.clear()
        # Восстанавливаем значения по умолчанию
        self.org_inn_entry.setText("введите ИНН аттестовывающей организации")
        self.org_title_entry.setText("введите название аттестовывающей организации")
        self.employer_org_inn_entry.setText("введите ИНН работодателя")
        self.employer_org_title_entry.setText("введите название работодателя")
        self.update_selected_count()

    def clear_partial_entries(self):
        self.surname_entry.clear()
        self.name_entry.clear()
        self.patronymic_entry.clear()
        self.snils_entry.clear()

    def parse_full_name(self):
        full_name = self.full_name_entry.text().strip()
        parts = full_name.split()
        if len(parts) == 3:
            self.surname_entry.setText(parts[0])
            self.name_entry.setText(parts[1])
            self.patronymic_entry.setText(parts[2])
            self.patronymic_entry.setFocus()
        else:
            QMessageBox.warning(self, "Ошибка", "Введите Фамилию, Имя и Отчество через пробел (три слова).")

    def try_autocomplete_snils_and_position(self):
        surname = self.surname_entry.text().strip()
        name = self.name_entry.text().strip()
        patronymic = self.patronymic_entry.text().strip()

        if surname and name and patronymic:
            suggest_autofill_data(self, self.conn, surname, name, patronymic, self.snils_entry, self.position_entry)

    def submit_data(self):
        surname = self.surname_entry.text().strip()
        name = self.name_entry.text().strip()
        patronymic = self.patronymic_entry.text().strip()
        snils = self.snils_entry.text().strip()
        isForeignSnils = 1 if self.isForeignSnils_checkbox.isChecked() else 0
        foreignSnils = self.foreignSnils_entry.text().strip()
        citizenship = self.citizenship_entry.text().strip()
        position = self.position_entry.text().strip()
        org_inn = self.org_inn_entry.text().strip()
        org_title = self.org_title_entry.text().strip()
        employer_org_inn = self.employer_org_inn_entry.text().strip()
        employer_org_title = self.employer_org_title_entry.text().strip()
        selected_items = self.learn_program_list.selectedItems()
        selected_program_ids = [item.data(Qt.UserRole) for item in selected_items]
        is_passed = 1 if self.is_passed_checkbox.isChecked() else 0
        protocol_number = self.protocol_number_entry.text().strip()
        exam_date = self.exam_date_entry.text().strip()
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        required_fields = [surname, name, snils, exam_date, protocol_number]
        if not all(required_fields):
            QMessageBox.warning(self, "Ошибка", "Все обязательные поля не заполнены.")
            return

        if not validate_snils(snils):
            reply = QMessageBox.question(
                self,
                "Неверный СНИЛС",
                f"СНИЛС не прошел проверку.\nВведённый СНИЛС: {snils}\n\nСохранить данные с этим СНИЛС?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        if not validate_date(exam_date):
            QMessageBox.warning(self, "Ошибка", "Неверный формат даты. Ожидается ДД.ММ.ГГГГ")
            return

        if "/" in protocol_number:
            QMessageBox.warning(self, "Ошибка", "Номер протокола не должен содержать символ '/'")
            return

        if not selected_program_ids:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну учебную программу.")
            return

        try:
            with self.conn:
                for pid in selected_program_ids:
                    self.conn.execute(
                        '''
                        INSERT INTO users (
                            surname, name, patronymic, snils, isForeignSnils, foreignSnils, citizenship,
                            position, org_inn, org_title, employer_org_inn, employer_org_title,
                            learn_program_id, is_passed, protocol_number, exam_date, entry_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            surname, name, patronymic, snils, isForeignSnils, foreignSnils, citizenship,
                            position, org_inn, org_title, employer_org_inn, employer_org_title,
                            pid, is_passed, protocol_number, exam_date, now
                        )
                    )
            QMessageBox.information(self, "Успех", "Данные успешно сохранены!")
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def show_protocol_info(self):
        dialog = ProtocolInfoDialog(self.conn, self)
        dialog.exec_()

    def create_xml_filtered(self):
        target_protocol_number = self.protocol_number_for_xml_entry.text().strip()
        if not target_protocol_number:
            QMessageBox.warning(self, "Ошибка", "Введите номер протокола для создания XML.")
            return
        create_xml(self.conn, target_protocol_number)
        QMessageBox.information(self, "Успех", "XML-файл успешно создан.")

    def create_xml_all(self):
        create_xml(self.conn)
        QMessageBox.information(self, "Успех", "XML-файл успешно создан.")

    def create_database(self):
        try:
            cursor = self.conn.cursor()
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
            self.conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))

    def closeEvent(self, event):
        self.conn.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
