"""
Authors: Jenna Mehto & Vilma Lehto (GUI), Janina Montonen & Pinja Koivisto (back-end)
Course: Health Software Development Project, Spring 2024
Description: The application conforms to an existing risk calculation site called FINRISKI.
The calculator’s algorithms are based on a research article, where the risk percentage is determined
for both stroke and heart attack as well as their combined risk.
The vital sign and other known information are fetched from the HL7 FHIR database,
that includes for example blood pressure, age and gender of the patient.
The rest of the needed information such as diabetes and smoking habits are filled in manually
via questionnaire. The calculated risks are visualized as bar charts and percentages.
"""

import tkinter as tk
from tkinter import ttk
import json
import requests
from pprint import pprint
from datetime import date, datetime
from math import exp

user = {
    'Name' : '',
    'Admin' : False
}

patient = {
    'Id':'',
    'Name':'',
    'Age':'',
    'Blood pressure':'',
    'Cholesterol':'',
    'HDL':'',
    'Smoke':'',
    'Diabetes':''
}

result = {
    'Heart attack': 0,
    'Stroke': 0,
    'Both': 0
}

patient_ids = set()

class SimpleFHIRClient(object):
    """
    Retrieves patient data from the DHIR database and processes it into json format
    """
    def __init__(self, server_url, server_user, server_password, debug=False):
        self.debug = debug
        self.server_url = server_url
        self.server_user = server_user
        self.server_password = server_password

    def getAllPatients(self):
        requesturl = self.server_url + "/Patient?_format=json"
        entries = self._get_json(requesturl)["entry"]
        return [entry["resource"] for entry in entries]

    def getAllDataForPatient(self, patient_id):
        requesturl = self.server_url + "/Patient/" + \
            patient_id + "$everything?_format=json"
        return self._get_json(requesturl)["entry"]

    def _get_json(self, requesturl):
        response = requests.get(requesturl,
                                auth=(self.server_user, self.server_password))
        response.raise_for_status()
        result = response.json()
        if self.debug:
            pprint(result)
        return result


client = SimpleFHIRClient(
    server_url="",
    server_user="",
    server_password="")

all_patients = client.getAllPatients()


def getBorn(id):
    """
    Get the date (year-month-day) from the patient
    """
    for patient_record in all_patients:
        if patient_record["id"] == id:
            born = datetime.strptime(patient_record['birthDate'], '%Y-%m-%d')
    return born


def definePatientIds():
    """
    Defines the patient ids into a global set
    """
    all_patients = client.getAllPatients()

    for patient_record in all_patients:
        patient_ids.add(patient_record["id"])

    pprint(patient_ids)


def getGender(id):
    """
    Get the gender of the patient
    """
    all_patients = client.getAllPatients()
    for patient_record in all_patients:
        if patient_record["id"] == id:
            patient_gender = patient_record["gender"]
    return patient_gender


def getName(id):
    """
    Get the name of the patient
    """
    all_patients = client.getAllPatients()
    for patient_record in all_patients:
        if  patient_record["id"] == id:
            patient_name_given = patient_record["name"][0]["given"][0]
            patient_name_family = patient_record["name"][0]["family"][0]
            patient_name = patient_name_given + ' ' + patient_name_family
    return patient_name


def updatePatient(patient_id):
    """
    Updating the patient struct with fetching the values from FHIR
    """
    BP = getBloodPressure(patient_id)
    HDL = getHDL(patient_id)
    cholest = getCholesterolValue(patient_id)
    born = getBorn(patient_id)
    age = getAge(born)
    gender = getGender(patient_id)
    name = getName(patient_id)

    patient['Id'] = patient_id
    patient['Name'] = name
    patient['Gender'] = gender
    patient['Age'] = age
    patient['Blood pressure'] = BP
    patient['Cholesterol'] = cholest
    patient['HDL'] = HDL


def calculateStroke(BP, HDL, age, smoke, db, gender):
    """
    Calculating the risk of a patient to have a stroke
    """
    if gender == 'female':
        risk = (1 / (1 + exp(9.553 - 0.085 * float(age)- 0.613 * smoke
                             + 0.623 * float(HDL) - 0.012 * float(BP) - 0.914 * db)))

        risk_percentage = risk * 100
    else:
        risk = (1 / (1 + exp(9.928 - 0.083 * float(age)- 0.369 * smoke
                             + 0.329 * float(HDL) - 0.014 * float(BP) - 0.705 * db)))
        risk_percentage = risk * 100

    return round(risk_percentage, 1)


def calculateCAD(BP, HDL, ch, age, smoke, db, gender):
    """
    Calculating the risk of a patient to have CAD
    """
    if gender == 'female':
        risk = (1 / (1 + exp(11.250 - 0.095 * float(age) - 0.639 * smoke - 0.244 * float(ch)
                             + 0.845 * float(HDL) - 0.013 * float(BP) - 1.315 * db)))
        risk_percentage = risk * 100
    else:
        risk = (1 / (1 + exp(9.081 - 0.075 * float(age) - 0.579 * smoke + 0.329 - 0.320 * float(ch)
                             + 1.082 * float(HDL) - 0.011 * float(BP) - 0.729 * db)))
        risk_percentage = risk * 100

    return round(risk_percentage, 1)


def calculateBoth(stroke_risk, CAD_risk):
    """
    Calculating the risk of a patient to have a stroke and CAD
    """
    risk = 1 - ((1 - (CAD_risk/100)) * (1 - (stroke_risk/100)))
    risk_percentage = risk * 100
    return round(risk_percentage, 1)


def updateResult(patient_id):
    """
    Updating the result struct with fetching the values from the risk calculation functions
    """
    HT = calculateCAD(patient['Blood pressure'], patient['HDL'], patient['Cholesterol'], patient['Age'], patient['Smoke'], patient['Diabetes'], patient['Gender'])
    stroke = calculateStroke(patient['Blood pressure'], patient['HDL'], patient['Age'], patient['Smoke'], patient['Diabetes'], patient['Gender'])
    both = calculateBoth(stroke, HT)

    result['Heart attack'] = HT
    result['Stroke'] = stroke
    result['Both'] = both


def getAge(born):
    """
    Calculating the age in years
    """
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return age


def getBloodPressure(id):
    """
    Get systolic blood pressure from patient
    """

    BP_list = []
    all_data = client.getAllDataForPatient(id)
    x = range(0, len(all_data))

    for i in x:
        try:
            if all_data[i]['resource']['code']:
                if all_data[i]['resource']['code']['text'] == 'Systolic blood pressure':
                    BP_list.append((all_data[i]['resource']['valueQuantity']['value']))

        except KeyError:
            continue

    if len(BP_list) == 0:
        BP_value = 0

    else:
        BP_value = BP_list[0]

    return BP_value


def getCholesterolValue(id):
    """
    Get cholesterol value from patient
    """
    CH_list = []
    all_data = client.getAllDataForPatient(id)
    x = range(0, len(all_data))

    for i in x:
        try:
            if all_data[i]['resource']['code']:
                if all_data[i]['resource']['code']['text'] == 'Cholest SerPl-mCnc':
                    CH_list.append(all_data[i]['resource']['valueQuantity']['value'])

        except KeyError:
            continue

    if len(CH_list) == 0:
        CH_value = 0
    else:
        CH_value = CH_list[0]

    return round(CH_value * 10/386.65, 1)   # change from mmHg to mmol/L


def getHDL(id):
    """
    Get HDL ('good cholesterol') value from the patient
    """
    HDL_list = []
    all_data = client.getAllDataForPatient(id)
    x = range(0, len(all_data))

    for i in x:
        try:
            if all_data[i]['resource']['code']:
                if all_data[i]['resource']['code']['text'] == 'HDLc SerPl-mCnc':
                    HDL_list.append(all_data[i]['resource']['valueQuantity']['value'])

        except KeyError:
            continue

    if len(HDL_list) == 0:
        HDL_value = 0
    else:
        HDL_value = HDL_list[0]

    return round(HDL_value * 10/386.65, 1)   # change from mmHg to mmol/L


def results_histogram(data, canvas, width=400, height=300, bar_color="#90B2DF"):
    """
    Plots the histograms that visualize the risk percentages
    """
    height_in_pix = 250
    width_in_pix = 60
    x_start = 100

    canvas.create_line(40, 275, 400, 275)
    canvas.create_line(40, 250, 400, 250)
    canvas.create_line(40, 225, 400, 225)
    canvas.create_line(40, 200, 400, 200)
    canvas.create_line(40, 175, 400, 175)
    canvas.create_line(40, 150, 400, 150)
    canvas.create_line(40, 125, 400, 125)
    canvas.create_line(40, 100, 400, 100)
    canvas.create_line(40, 75, 400, 75)
    canvas.create_line(40, 50, 400, 50)
    canvas.create_line(40, 25, 400, 25)
    canvas.create_line(50, 15, 50, 275)

    for key in data.keys():
        pprint(key)
        pprint(data[key])

        x0 = x_start
        y0 = (250 - round(250*(data[key]/100)))+25
        x1 = x0 + width_in_pix
        y1 = 275

        x_start += 95

        pprint(y0)
        pprint(round(250*(data[key]/100)))

        canvas.create_rectangle(x0, y0, x1, y1, fill=bar_color)


    canvas.create_text(130, 285, text="Heart attack", fill="black",
                       font=("Helvetica", 11))
    info_txt_1 = "{} %".format(result['Heart attack'])
    canvas.create_text(130, 295, text=info_txt_1, fill="#4C70AB",
                       font=("Helvetica", 11))
    canvas.create_text(225, 285, text="Stroke", fill="black",
                       font=("Helvetica", 11))
    info_txt_2 = "{} %".format(result['Stroke'])
    canvas.create_text(227, 295, text=info_txt_2, fill="#4C70AB",
                       font=("Helvetica", 11))
    canvas.create_text(320, 285, text="Both", fill="black",
                       font=("Helvetica", 11))
    info_txt_3 = "{} %".format(result['Both'])
    canvas.create_text(323, 295, text=info_txt_3, fill="#4C70AB",
                       font=("Helvetica", 11))

    canvas.create_text(25, 25, text="100", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 50, text="90", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 75, text="80", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 100, text="70", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 125, text="60", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 150, text="50", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 175, text="40", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 200, text="30", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 225, text="20", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 250, text="10", fill="black",
                       font=("Helvetica", 11))
    canvas.create_text(25, 275, text="0", fill="black",
                       font=("Helvetica", 11))


class ContainerPages (tk.Tk):
    """
    Defines the interface as a class
    """
    patient = {}
    pages = {}

    def __init__(self):
        tk.Tk.__init__(self)

        # Defined size of the window
        self.geometry("800x600")

        self.display_startpage()
        definePatientIds()

    def display_startpage(self):
        """
        The first window of the program (login)
        """
        frames = tk.Frame(self)

        # The frames are packed within parent widget
        frames.grid(row=1, column=0, sticky="nsew")
        frames.grid_rowconfigure(0, weight=1)
        frames.grid_columnconfigure(0, weight=1)

        name = StartPage.__name__
        frame = StartPage(parent=frames, controller=self)
        self.pages[name] = frame

        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()

    def display_searchpage(self):
        """
        Patient search page
        """
        frames = tk.Frame(self)

        # The frames are packed within parent widget
        frames.grid(row=1, column=0, sticky="nsew")
        frames.grid_rowconfigure(0, weight=1)
        frames.grid_columnconfigure(0, weight=1)

        name = SearchPage.__name__
        frame = SearchPage(parent=frames, controller=self)
        self.pages[name] = frame

        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()

    def display_infopage(self):
        """
        Patient information is retrieved and shown, other relevant information can be entered
        """
        frames = tk.Frame(self)

        # The frames are packed within parent widget
        frames.grid(row=1, column=0, sticky="nsew")
        frames.grid_rowconfigure(0, weight=1)
        frames.grid_columnconfigure(0, weight=1)

        name = InfoPage.__name__
        frame = InfoPage(parent=frames, controller=self)
        self.pages[name] = frame

        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()

    def display_resultpage(self):
        """
        Displays the result page with bar charts
        """
        frames = tk.Frame(self)

        # The frames are packed within parent widget
        frames.grid(row=1, column=0, sticky="nsew")
        frames.grid_rowconfigure(0, weight=1)
        frames.grid_columnconfigure(0, weight=1)

        name = ResultPage.__name__
        frame = ResultPage(parent=frames, controller=self)
        self.pages[name] = frame

        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()

    def display_frame(self, name):
        page = self.pages[name]
        page.tkraise()



class StartPage(tk.Frame):
    """
    Class defined for the first page, where the user logs in
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        login_information = {'Jenna' : 'Päivänsäde', 'Pinja' : 'Poutapilvi', 'Janina' : 'Sadekuuro', 'Vilma' : 'Ukkosmyrsky'}

        def checkLogin():

            if len(password.get()) == 0 or len(username.get()) == 0:
                error_text.set("Wrong username or password!")

            elif password.get() != login_information[username.get()]:
                error_text.set("Wrong username or password!")

            else:
                user['Name'] = username.get()
                controller.display_searchpage()

                username.set("")
                password.set("")

            error_lbl.config(text=error_text.get())

        #Buttons as navigation
        nav_btn1 = tk.Button(self, text="Search patient", fg="#4C70AB",
                             width=15, height=2,
                             state=tk.DISABLED)
        nav_btn2 = tk.Button(self, text="Information form", fg="#4C70AB",
                             width=15, height=2,
                            state=tk.DISABLED)
        nav_btn3 = tk.Button(self, text="Results", fg="#4C70AB", width=15,
                             height=2,
                             state=tk.DISABLED)

        nav_btn1.grid(row=0, column=0, padx=0, pady=0)
        nav_btn2.grid(row=0, column=1, padx=0, pady=0)
        nav_btn3.grid(sticky="w", row=0, column=2, padx=0, pady=0)

        #empty rows
        self.grid_rowconfigure(1, minsize=50)
        self.grid_rowconfigure(4, minsize=70)


        #headline for the page
        label = tk.Label(self, text="State of Health - Risk calculator", font=("Helvetica", 16), fg="#4C70AB")
        label.grid(row=4, column=2, columnspan=5, pady=10)

        #create labels
        username_lbl = tk.Label(self, text="Username:")
        username_lbl.grid(sticky="e", column=0, row=5, columnspan=2, pady=5)

        password_lbl = tk.Label(self, text="Password:")
        password_lbl.grid(sticky="e", column=0, row=6, columnspan=2, pady=5)

        #create entry lines
        username = tk.StringVar()
        password = tk.StringVar()

        username_entry = tk.Entry(self, textvariable=username)
        username_entry.grid(sticky="w", row=5, column=2, padx=5, pady=5)

        password_entry = tk.Entry(self, show="*", textvariable=password)
        password_entry.grid(sticky="w", row=6, column=2,padx=5, pady=5)

        #create login button
        button = tk.Button(self, text="Login", command=checkLogin)
        button.grid(row=8, column=3)

        #create error message
        error_text = tk.StringVar()
        error_lbl = tk.Label(self, text=error_text.get(), fg="red")
        error_lbl.grid(row=7, column=1, columnspan=3)


class SearchPage(tk.Frame):
    """
    Class for the search page (second window), where patient can be searched with an ID
    """
    patient_ids = {'12345'}

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        # Buttons as navigation
        nav_btn1 = tk.Button(self, text="Search patient", fg="#4C70AB", width=15, height=2,
                             command=lambda: controller.display_searchpage())
        nav_btn2 = tk.Button(self, text="Information form", fg="#4C70AB", width=15, height=2,
                             state=tk.DISABLED)
        nav_btn3 = tk.Button(self, text="Results", fg="#4C70AB", width=15, height=2,
                             state=tk.DISABLED)

        nav_btn1.grid(row=0, column=0, rowspan=2, padx=0, pady=0)
        nav_btn2.grid(row=0, column=1, rowspan=2, padx=0, pady=0)
        nav_btn3.grid(row=0, column=2, rowspan=2, padx=0, pady=0)

        # Create empty column
        self.grid_columnconfigure(3, minsize=50)
        self.grid_columnconfigure(4, minsize=150)

        # Create user info in the right corner
        user_txt = 'Käyttäjä ' + user['Name']
        user_lbl = tk.Label(self, text=user_txt,
                            font=('Arial', 11), fg="#4C70AB")
        user_lbl.grid(row=0, column=5, padx=0, pady=0, sticky="e")

        # Create logout button
        logout_btn = tk.Button(self, text="Log Out", highlightthickness = 0,
                               font=('Arial', 11), fg="#4C70AB", bd = 0,
                               command=lambda: controller.display_startpage())
        logout_btn.grid(row=1, column=5, padx=0, pady=0)

        # Create empty rows to align elements
        self.grid_rowconfigure(2, minsize=150)
        self.grid_rowconfigure(6, minsize=50)

        # Create main labels for calculator name and label for entry
        name_lbl = tk.Label(self, text="Risk Calculator", font=("Helvetica", 16),
                            fg="#4C70AB")
        patient_lbl = tk.Label(self, text="Patient id:", fg="#4C70AB")

        name_lbl.grid(row=4, column=1, columnspan=2, padx=5, pady=20, sticky='w')
        patient_lbl.grid(row=5, column=1, padx=0, pady=5)

        # Create entry line
        entry_id = tk.Entry(self, width=20)
        entry_id.grid(row=5, column=2, columnspan=3, padx=0, pady=5, sticky='w')

        # Create search button
        search_btn = tk.Button(self, text="Search", width=5,
                             command=lambda: self.check_patient_id(self, patient_ids, entry_id))
        search_btn.grid(row=7, column=3, padx=5, pady=5)

    def check_patient_id(self, frame, ids, value):
        entry_str = value.get()

        if entry_str in ids:
            updatePatient(entry_str)
            self.controller.display_infopage()

        else:
            info_lbl = tk.Label(self, text="Wrong patient id", fg="red")
            info_lbl.grid(row=6, column=2, padx=5, pady=5)



class InfoPage(tk.Frame):
    """
    Patient information window, data retrieved from FHIR or entered manually by check-boxes.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.columnconfigure(4, minsize=100, weight=0)

        errors = tk.BooleanVar()
        errors.set(False)

        diabetes_result = tk.IntVar(0)
        smoking_result = tk.IntVar(0)

        #Function to check the checkboxes
        def checkBoxes():

            #if both smoking boxes are checked
            if smoking_boolean_yes.get() and smoking_boolean_no.get():
                smoking_text.set("Check only one box")
                errors.set(True)

            #if  neither of the smoking boxes is checked
            elif smoking_boolean_yes.get()==False and smoking_boolean_no.get()==False:
                smoking_text.set("Check one box")
                errors.set(True)

            #correct way, one of the smoking boxes is checked
            else:
                smoking_text.set("")
                #if patient smokes, set the value to 1
                if smoking_boolean_yes.get():
                    smoking_result.set(1)
                #if the patient doesn't smoke, set the value to 0
                elif smoking_boolean_no.get:
                    smoking_result.set(0)

            #if both diabetes boxes are checked
            if diabetes_boolean_yes.get() and diabetes_boolean_no.get():
                diabetes_text.set("Check only one box")
                errors.set(True)

            #if neither of the diabetes boxes is checked
            elif diabetes_boolean_yes.get()==False and diabetes_boolean_no.get()==False:
                diabetes_text.set("Check one box")
                errors.set(True)

            #correct situation, one of the boxes is checked
            else:
                diabetes_text.set("")
                #if the patient has diabetes, set the value to 1
                if diabetes_boolean_yes.get():
                    diabetes_result.set(1)
                #if the patient does not have diavetes, set the value to 0
                elif diabetes_boolean_no.get():
                    diabetes_result.set(0)

            smoking_error.config(text=smoking_text.get())
            diabetes_error.config(text=diabetes_text.get())



        #function for checking that cholesterol levels are in correct range
        def checkCholesterol():
            HDL_float=0
            cl_float=0

            try:
                HDL_text.set("")
                HDL_float = float(HDL.get())

            except ValueError:
                errors.set(True)
                HDL_text.set("Check HDL cholesterol level")

            try:
                cl_text.set("")
                cl_float = float(cl.get())

            except ValueError:
                errors.set(True)
                cl_text.set("Check cholesterol level")


            if HDL_float < 0.3 or HDL_float > 5:
                errors.set(True)
                HDL_text.set("Check HDL cholesterol level")

            if cl_float < 2 or cl_float > 20:
                errors.set(True)
                cl_text.set("Check cholesterol level")

            HDL_error.config(text=HDL_text.get())
            cl_error.config(text=cl_text.get())


        #funktion for checking that age and name are in correct format
        def checkBasicInformation():

            #check that age is number
            try:
                age_text.set("")
                age_number = int(age.get())

            except ValueError:
                errors.set(True)
                age_text.set("Check patient's age")

            #init the name testing
            name_text.set("")
            name_chars = list(name.get())

            for c in name_chars:

                #name can include space or -
                if c == "-" or c == " ":
                    continue

                #if name includes other non-alphabet chars
                elif c.isalpha() == False:

                    #set error
                    name_text.set("Check patient's name")
                    errors.set(True)

            age_error.config(text=age_text.get())
            name_error.config(text=name_text.get())


        #function for checking the blood pressure
        def checkBP():

            systolic = 0
            bp_text.set("")

            #check that the numbe is float
            try:
                systolic = float(bp.get())

            except ValueError:
                bp_text.set("Check blood pressure")
                errors.set(True)

            #check that bp is within the limits
            if systolic < 80 or systolic > 240:
                bp_text.set("Check blood pressure")


            #configure the error message
            bp_error.config(text=bp_text.get())


         #Funktion that is called to move on to result page
        def moveOn():

            #alusteaan virheiden tarkastelu
            errors.set(False)

            checkBasicInformation()
            checkBoxes()
            checkCholesterol()
            checkBP()

            if errors.get():
                pass

            #if all is good we will save the information and move on
            else:
                patient["Name"] = name.get()
                patient["Age"] = age.get()
                patient["Blood pressure"] = bp.get()
                patient["Cholesterol"] = cl.get()
                patient["HDL"] = HDL.get()
                patient["Smoke"] = smoking_result.get()
                patient["Diabetes"] = diabetes_result.get()

                pprint(patient)
                updateResult(patient["Id"])
                self.controller.display_resultpage()


        #headline for the page
        label = tk.Label(self, text="Patient's information", font=("Helvetica", 16), fg="#4C70AB")
        label.grid(row=3, column=2, columnspan=2, pady=10)

        # Buttons as navigation
        nav_btn1 = tk.Button(self, text="Search patient", fg="#4C70AB",
                             width=15, height=2,
                             command=lambda: controller.display_searchpage())
        nav_btn2 = tk.Button(self, text="Information form", fg="#4C70AB",
                             width=15, height=2,
                             command=lambda: controller.display_infopage())
        nav_btn3 = tk.Button(self, text="Results", fg="#4C70AB", width=15,
                             height=2,
                             state=tk.DISABLED)

        # Create user info in the right corner
        user_txt = 'Käyttäjä ' + user['Name']
        print(user_txt)
        print(user['Name'])
        user_lbl = tk.Label(self, text=user_txt, font=('Arial', 11), fg="#4C70AB")
        user_lbl.grid(row=0, column=4, padx=0, pady=0, sticky="e")

        # Create logout button
        logout_btn = tk.Button(self, text="Log Out    ", font=('Arial', 11), highlightthickness = 0, fg="#4C70AB", bd = 0,
                               command=lambda: controller.display_startpage())
        logout_btn.grid(row=1, column=4, sticky='e')

        nav_btn1.grid(row=0, column=0, rowspan=2)
        nav_btn2.grid(row=0, column=1, rowspan=2)
        nav_btn3.grid(sticky="w", row=0, column=2, rowspan=2)

        #Empty row to line the elements
        self.grid_rowconfigure(5, minsize=50)

        #create the labels:
        id_lbl = tk.Label(self, text="Patient's id")
        id_lbl.grid(sticky = "E", row=5, column=0, columnspan=2, padx=10, pady=10)

        name_lbl = tk.Label(self, text="Patient's name")
        name_lbl.grid(sticky="E", row=6, column=0, columnspan=2, padx=10, pady=10)

        age_lbl = tk.Label(self, text="Patient's age")
        age_lbl.grid(sticky="E", row=7, column=0, columnspan=2, padx=10, pady= 0)

        bp_lbl = tk.Label(self, text="Blood pressure")
        bp_lbl.grid(sticky="E", row=8, column=0, columnspan=2, padx=10, pady=10)

        cholesterol_lbl = tk.Label(self, text="Cholesterol level")
        cholesterol_lbl.grid(sticky="E", row=9, column=0, columnspan=2, padx=10, pady=10)

        HDLcholesterol_lbl = tk.Label(self, text="HDL cholesterol level")
        HDLcholesterol_lbl.grid(sticky="E", row=10, column=0, columnspan=2, padx=10, pady=10)

        smoking_lbl = tk.Label(self, text="Does patient smoke?")
        smoking_lbl.grid(sticky="E", row=11, column=0, columnspan=2, padx=10, pady=10)

        diabetes_lbl = tk.Label(self, text="Does patient has diabetes?")
        diabetes_lbl.grid(sticky="E", row=12, column=0, columnspan=2, padx=10, pady=10)

        #create entrylines
        id =tk.StringVar()
        id_entry = tk.Entry(self, width=32, textvariable=id)
        id.set(patient['Id'])
        id_entry.grid(sticky='w', row=5, column=2, columnspan=2, pady=5)

        name = tk.StringVar()
        name_entry = tk.Entry(self, width=32, textvariable=name)
        name.set(patient["Name"])
        name_entry.grid(sticky="w", row=6, column=2, columnspan=2, pady=5)

        age = tk.StringVar()
        age_entry = tk.Entry(self, width=32, textvariable=age)
        age.set(patient["Age"])
        age_entry.grid(sticky="w", row=7, column=2, columnspan=2, pady=5)

        bp = tk.StringVar()
        bp_entry = tk.Entry(self, width=32, textvariable=bp)
        bp.set(patient["Blood pressure"])
        bp_entry.grid(sticky="w", row=8, column=2, columnspan=2, pady=5)

        cl = tk.StringVar()
        cholesterol_entry = tk.Entry(self, width=32, textvariable=cl)
        cl.set(patient["Cholesterol"])
        cholesterol_entry.grid(sticky="w", row=9, column=2, columnspan=2, pady=5)

        HDL = tk.StringVar()
        HDLcholesterol_entry = tk.Entry(self, width=32, textvariable=HDL)
        HDL.set(patient["HDL"])
        HDLcholesterol_entry.grid(sticky="w", row=10, column=2, columnspan=2, pady=5)

        #create checkboxes
        smoking_boolean_yes = tk.BooleanVar()
        smoking_yes = tk.Checkbutton(self, text = "Yes", variable = smoking_boolean_yes, onvalue = True, offvalue = False)
        smoking_yes.grid(sticky = "w", row = 11, column = 2)

        smoking_boolean_no = tk.BooleanVar()
        smoking_no = tk.Checkbutton(self, text="No",variable=smoking_boolean_no, onvalue=True, offvalue=False)
        smoking_no.grid(sticky="e", row=11, column=2)

        diabetes_boolean_yes = tk.BooleanVar()
        diabetes_yes = tk.Checkbutton(self, text="Yes",variable=diabetes_boolean_yes, onvalue=True, offvalue=False)
        diabetes_yes.grid(sticky="w", row=12, column=2)

        diabetes_boolean_no = tk.BooleanVar()
        diabetes_no = tk.Checkbutton(self, text = "No",variable = diabetes_boolean_no, onvalue=True, offvalue=False)
        diabetes_no.grid(sticky="e", row=12, column=2)

        #create calculate button
        calculate_btn = ttk.Button(self, text="Calculate results", command=moveOn)
        calculate_btn.grid(row=14, column=4, sticky='w')

        #create space for boxes error messages
        smoking_text = tk.StringVar()
        diabetes_text = tk.StringVar()
        smoking_text.set("")
        diabetes_text.set("")

        smoking_error = tk.Label(self, text=smoking_text.get(), fg="red", width=15, anchor="w")
        smoking_error.grid(sticky="w", row=11, column=3)

        diabetes_error = tk.Label(self, text=diabetes_text.get(), fg="red", width=15, anchor="w")
        diabetes_error.grid(sticky="w", row=12, column=3)

        #create an age error message
        age_text = tk.StringVar("")
        age_error = tk.Label(self, text=age_text.get(), fg="red", width=26, anchor="w")
        age_error.grid(sticky="w", row=7, column=4)

        #create a name error message
        name_text = tk.StringVar("")
        name_error = tk.Label(self, text=name_text.get(), fg="red", width=26, anchor="w")
        name_error.grid(sticky="w", row=6, column=4)

        #create a cholesterol error messages
        cl_text = tk.StringVar("")
        HDL_text = tk.StringVar("")
        cl_error = tk.Label(self, text=cl_text.get(), fg="red", width=26, anchor="w")
        HDL_error = tk.Label(self, text=HDL_text.get(), fg="red", width=26, anchor="w")
        cl_error.grid(sticky="w", row=9, column=4)
        HDL_error.grid(sticky="w", row=10, column=4)

        #create a bloop pressure error message
        bp_text = tk.StringVar("")
        bp_error = tk.Label(self, text=bp_text.get(), fg="red", width=26, anchor="w")
        bp_error.grid(sticky="w", row=8, column=4)


class ResultPage(tk.Frame):
    """
    The last window that visualizes the results as bar charts.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        # Buttons as navigation
        nav_btn1 = tk.Button(self, text="Search patient", fg="#4C70AB", width=15, height=2,
                             command=lambda: controller.display_searchpage())
        nav_btn2 = tk.Button(self, text="Information form", fg="#4C70AB", width=15, height=2,
                             command=lambda: controller.display_infopage())
        nav_btn3 = tk.Button(self, text="Results", fg="#4C70AB", width=15, height=2,
                             command=lambda: controller.display_resultpage())

        nav_btn1.grid(row=0, column=0, rowspan=2, padx=0, pady=0)
        nav_btn2.grid(row=0, column=1, rowspan=2, padx=0, pady=0)
        nav_btn3.grid(row=0, column=2, rowspan=2, padx=0, pady=0)

        # Create empty column
        self.grid_columnconfigure(3, minsize=50)
        self.grid_columnconfigure(4, minsize=159)

        # Create user info in the right corner
        user_txt = 'Käyttäjä ' + user['Name']
        user_lbl = tk.Label(self, text=user_txt,
                            font=('Arial', 11), fg="#4C70AB")
        user_lbl.grid(row=0, column=5, padx=0, pady=0, sticky="e")

        # Create logout button
        logout_btn = tk.Button(self, text="Log Out", highlightthickness = 0,
                               font=('Arial', 11), fg="#4C70AB", bd = 0,
                               command=lambda: controller.display_startpage())
        logout_btn.grid(row=1, column=5, padx=0, pady=0)

        # Empty rows to align elements
        self.grid_rowconfigure(2, minsize=80)
        self.grid_rowconfigure(5, minsize=25)

        # Create title label for the page
        name_lbl = tk.Label(self, text="Results",
                            font=("Helvetica", 16), fg="#4C70AB")
        name_lbl.grid(row=4, column=0, columnspan=3, padx=120, pady=20, sticky='w')

        canvas = tk.Canvas(self, width=400, height=300)
        canvas.grid(row=6, column=0, rowspan=1, columnspan=6, padx=80, pady=5, sticky='w')

        info_txt = "The risk of heart attack\nis {}%, the risk of\nstroke is {}%, and the\ncombined risk is {}%".format(
            result['Heart attack'], result['Stroke'], result['Both'])
        info_lbl = tk.Label(self, text=info_txt, background="#6F8CBB", fg="white")
        info_lbl.grid(row=6, column=4, columnspan=2)

        results_histogram(result, canvas)

ui = ContainerPages()
ui.mainloop()


