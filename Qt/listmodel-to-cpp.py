#!/usr/bin/python3

import os
import re
import sys

# make first letter big
def first_big_case(s):
    return s[0].upper() + s[1:]

def generate_cpp_class(qml_file_path):
    base_name = os.path.splitext(os.path.basename(qml_file_path))[0]
    class_name = base_name

    with open(qml_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # (1) Check if ListModel is the root element
    if not re.search(r'^\s*ListModel\s*{', content, re.MULTILINE):
        print("Error: QML file must contain ListModel as the root object.")
        sys.exit(1)

    # (2) Find ListElement properties and capture property name and value
    elements = re.findall(r'ListElement\s*{([^}]*)}', content, re.MULTILINE | re.DOTALL)
    num_elements = len(elements)
    if not elements:
        print("Error: No ListElement objects found.")
        sys.exit(1)

    values = dict()
    properties = []

    # First element defines the set of properties
    props = re.findall(r'(\w+)\s*:\s*(.*)', elements[0])
    properties = {prop for prop, _ in props}
    for prop in properties:
        values[prop] = []
    # Fill in values for element 0
    for prop, val in props:
        values[prop].append(val)
            
    for idx in range(1, num_elements):
        props = re.findall(r'(\w+)\s*:\s*(.*)', elements[idx])
        current_props = {prop for prop, _ in props}
        if current_props != properties:
            set_difference = properties.symmetric_difference(current_props)
            print(f"Error: All properties in model should be explicitly defined for every ListElement. Missing properties: {set_difference}")
            sys.exit(1)        
        # Fill in values
        for prop, val in props:
            values[prop].append(val)

    # convert properties set to list
    properties = sorted(properties)

    # Prepare C++ class
    h_content = f"#pragma once\n\n"
    h_content += "#include <QAbstractListModel>\n#include <QStringList>\n\n"
    h_content += f"class {class_name} : public QAbstractListModel\n{{\n    Q_OBJECT\npublic:\n"
    h_content += f"    explicit {class_name}(QObject *parent = nullptr);\n\n"

    # Enum Roles
    h_content += "    enum Roles {\n"
    for prop in properties:
        h_content += f"        {first_big_case(prop)}Role,\n"
    h_content += "    };\n\n"

    # Standard methods
    h_content += "    int rowCount(const QModelIndex &parent = QModelIndex()) const override;\n"
    h_content += "    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;\n"
    h_content += "    QHash<int, QByteArray> roleNames() const override;\n\n"

    # Private section
    h_content += "private:\n"

    for prop in properties:
        h_content += f"    QStringList m_{prop}s;\n"

    # (5) Insert method
    insert_args = ", ".join([f"const QString &{prop}" for prop in properties])
    h_content += f"\n    void insert({insert_args});\n"

    # Populate method
    h_content += "    void populateModel();\n};\n\n"

    # Create source file content
    cpp_content = f"#include \"{class_name.lower()}.h\"\n\n"
    cpp_content += f"{class_name}::{class_name}(QObject *parent)\n    : QAbstractListModel(parent)\n{{\n    populateModel();\n}}\n\n"

    # (6) rowCount, data, roleNames
    cpp_content += "// Returns the number of rows in the model\n"
    cpp_content += f"int {class_name}::rowCount(const QModelIndex &parent) const\n{{\n"
    cpp_content += "    if (parent.isValid())\n        return 0;\n"
    cpp_content += f"    return static_cast<int>(m_{properties[0]}s.size());\n}}\n\n"

    cpp_content += "// Returns data for each role\n"
    cpp_content += f"QVariant {class_name}::data(const QModelIndex &index, int role) const\n{{\n"
    cpp_content += "    if (!index.isValid())\n        return QVariant();\n\n"
    for prop in properties:
        cpp_content += f"    if (role == {first_big_case(prop)}Role)\n"
        cpp_content += f"        return m_{prop}s.at(index.row());\n"
    cpp_content += "\n    return QVariant();\n}\n\n"

    cpp_content += "// Returns role names to be used in QML\n"
    cpp_content += f"QHash<int, QByteArray> {class_name}::roleNames() const\n{{\n"
    cpp_content += "    QHash<int, QByteArray> roles;\n"
    for prop in properties:
        cpp_content += f"    roles[{first_big_case(prop)}Role] = \"{prop}\";\n"
    cpp_content += "    return roles;\n}\n\n"

    # (5) Insert method
    cpp_content += "// Inserts a single entry into the model\n"
    cpp_content += f"void {class_name}::insert({insert_args})\n{{\n"
    for prop in properties:
        cpp_content += f"    m_{prop}s.append({prop});\n"
    cpp_content += "}\n\n"

    # (6) Populate model by calling insert()
    cpp_content += "// Populates the model with static data\n"
    cpp_content += f"void {class_name}::populateModel()\n{{\n"
    for i in range(num_elements):
        args_call = ", ".join([f'{values[prop][i].replace("qsTr(", "tr(")}' for prop in properties])
        cpp_content += f"    insert({args_call});\n"
    cpp_content += "}\n"

    # Write output files
    output_dir = os.path.dirname(qml_file_path)
    header_file = os.path.join(output_dir, class_name.lower() + ".h")
    cpp_file = os.path.join(output_dir, class_name.lower() + ".cpp")

    with open(header_file, 'w', encoding='utf-8') as f:
        f.write(h_content)

    with open(cpp_file, 'w', encoding='utf-8') as f:
        f.write(cpp_content)

    print(f"Generated {header_file} and {cpp_file}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python qml_to_cpp_model_generator.py <path-to-qml-file>")
        sys.exit(1)

    qml_file = sys.argv[1]
    if not os.path.exists(qml_file):
        print(f"File '{qml_file}' does not exist.")
        sys.exit(1)

    generate_cpp_class(qml_file)
