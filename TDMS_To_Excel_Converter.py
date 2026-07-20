import os
from nptdms import TdmsFile
import pandas as pd

def tdms_to_excel(path):
    tdms_path, file_save_location = path.split(",")

    # 🔹 Extract filename without extension
    file_name = os.path.splitext(os.path.basename(tdms_path))[0]

    # 🔹 Create Excel path automatically
    excel_path = os.path.join(file_save_location, file_name + ".xlsx")

    tdms_file = TdmsFile.read(tdms_path)

    all_data = {}

    for group in tdms_file.groups():
        for channel in group.channels():
            all_data[f"{group.name}/{channel.name}"] = channel[:]

    df = pd.DataFrame(all_data)
    df.to_excel(excel_path, index=False)

    return f"SUCCESS:{excel_path}"

# print(tdms_to_excel("C:\\Users\\panch\\Downloads\\ 25_02_2026_11_00_44.tdms,D:\\Converter"))