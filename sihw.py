from contextlib import contextmanager
import pathlib
import zipfile
import shutil
import os
from selenium import webdriver
import argparse
from time import sleep
from pprint import pprint
from bs4 import BeautifulSoup
import pickle
import pyinputplus as pyip
from time import time
import sys

#Decoratoren und Kontexmanager -----------------------------------------------------------------------------------------------------------------------------
#Decorator für getElement funktionen, schaut 20s lang ob er ein Web element findet -> falls lade Probleme
def waiter(f):
    def inner(*args, **kwargs):
        i = 0
        while True:
            i += 1
            try:
                result = f(*args, **kwargs)
                break
            except Exception as e:
                sleep(.1)
                if i >= 200:
                    print('Internet ist wahrscheinlich off :( Error: ', e)
                    break
        return result
    return inner

#Stellt sicher das LMS daten gespeichert werden, selbst wenn es zu error kommt
@contextmanager
def lmsManager():
    lms = initLMS()
    try:
        yield lms
    finally:
        sleepLMS(lms)

#stellt sicher das der Driver geschlossen wird, selbst wenn es zu Error kommt, damit ram nicht zu voll wird
@contextmanager
def driverManager(usr, pwd, downloadFolder):
    driver = initDriver(downloadFolder)
    login(driver, usr, pwd)
    try:
        yield driver
    finally:
        print('Driver quitting the industry...')
        driver.quit()

#LMS Stuff ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def sleepLMS(lms):
    abs_dir = str(pathlib.Path(__file__).parent.absolute()) + '\\'
    with open(abs_dir + 'LmsInfo69', 'wb') as fh:
        pickle.dump(lms, fh)

def initLMS():
    abs_dir = str(pathlib.Path(__file__).parent.absolute()) + '\\'
    #versucht Daten zu laden und daraus LMS Objekt zu bauen
    try:
        with open(abs_dir + 'LmsInfo69', 'rb') as fh:
            lms = pickle.load(fh)
    except:
        #falls er das nicht kann, geht er davon aus das er dich nicht kennt und initialisiert Programm
        lms = setupLms()
    return lms

def setupLms():
    print('Hallo neuer Nutzer :) im folgenden brauche ich ein paar Daten')
    username, password = LmsLoginInfo()
    vorname, nachname = UserInfo()
    workFolder = setWorkFolder()

    return {
        'username':username,
        'password':password,
        'vorname':vorname,
        'nachname':nachname,
        'lastUpdate':time(),
        'updateIntervall':7200,
        'workFolder':workFolder,
        'Kurse' : None
        }
#Driver Stuff -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@waiter
def getElementByLink(plink, driver):
    return driver.find_element_by_link_text(plink)

@waiter
def getElement(xpath, driver):
    return driver.find_element_by_xpath(xpath)

def login(driver, username, password):
    #initialisiert driver falls es ihn noch nicht gibt -> optimierung... initDriver dauert lange nur machen wenn es nötig ist
    print('LMS Login...')
    driver.get('https://lms.at/register')
    getElement('//*[@id="email"]', driver).send_keys(username)
    getElement('//*[@id="password"]', driver).send_keys(password)
    getElement('/html/body/div[2]/div[4]/div/div/div[1]/form/div[3]/div[1]/button', driver).click()

def initDriver(downloadFolder):
    #Firefox options und profile config nicht anfassen
    print('initialisiere Driver...')
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2) #        #hier MIME-type einfügen, fall er ein File nicht runterladen kann
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/vnd.ms-powerpoint,application/mspowerpoint,application/x-mspowerpoint,application/powerpoint,application/mspowerpoint,application/vnd.ms-powerpoint,application/vnd.oasis.opendocument.text,application/vnd.openxmlformats-,application/x-zip-compressed,application/excel,application/vnd.ms-excel,application/plain,image/png,application/vnd.ms-powerpoint,application/mspowerpoint,application/powerpoint,image/png,image/pjpeg,image/jpeg,text/html,application/msword,text/plain,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.download.dir', downloadFolder)
    profile.set_preference('pdfjs.disabled', True)
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    driver = webdriver.Firefox(firefox_profile=profile, options=options)
    return driver

def DownloadHomeWorkTable(driver):
    print('Lade HTML-Table runter....')
    driver.get('https://lms.at/dotlrn/')
    getElement('//*[@id="hide-closed-homework"]', driver).click()
    table = getElement('/html/body/div[2]/div[4]/div/div/div/div[2]/div[2]/div/div[2]/div/table', driver).get_attribute('innerHTML')
    return table

def downloadInfo(driver, aufgabe):
    print('Get Info of', aufgabe['title'])
    if aufgabe == None or aufgabe['href'] == None:
        return None
    driver.get('https://lms.at/' + aufgabe['href'])
    instructions = getElement('/html/body/div[2]/div[4]/div/div/div[4]/div/div[5]', driver)
    downloads = getElement('/html/body/div[2]/div[4]/div/div/div[4]/div/div[6]/div[1]/table/tbody', driver)
    soup = BeautifulSoup(downloads.get_attribute('innerHTML'), 'html.parser')
    links = soup.find_all('a')
    downloads = [a.text for a in links]
    info = {
        'beschreibung':instructions.text,
        'downloads':downloads
    }
    return info

def downloadFiles(driver, aufgabe):
    if aufgabe['info'] != None and len(aufgabe['info']['downloads']) > 0:
        print('Downloading Files for', aufgabe['title'])

        driver.get('https://lms.at' + aufgabe['href'])
        for file in aufgabe['info']['downloads']:
            print('\tDownloading', file + '...')
            getElementByLink(file, driver).click()
            sleep(2)
            print('\tDownloaded', file)
        return

    print('--keine Dokumente vorhanden--')

def uploadFile(driver, file, aufgabe):
    driver.get('https://lms.at' + aufgabe['href'])
    getElementByLink('Abgabe hochladen', driver).click()
    getElement('//*[@id="upload_file"]', driver).send_keys(file)
    getElement('/html/body/div[2]/div[4]/div/div/form/table/tbody/tr[2]/td/input[1]', driver).click()
    getElement('//*[@id="save_assignment2"]', driver).click()
    return True
#Argumente Verarbeiten  ------------------------------------------------------------------------------------------------------------------------------------------------e
def initArgs():
    #Setzt Argumente 
    parser = argparse.ArgumentParser(description='LMS CLI von Ben :)')

    parser.add_argument('-i', '--info', dest='info',
     nargs='?', const=True, metavar='',
     help='öffnet info UI', default=False)

    parser.add_argument('-d', '--download', dest='download',
    nargs='?', const=True, metavar='',
    help='öffnet Download UI', default=False)

    parser.add_argument('-c', '--create', dest='create',
    nargs='?', const=True, metavar='',
    help='öffnet Create UI', default=False)

    parser.add_argument('-u', '--upload', dest='upload',
    nargs='?', const=True, metavar='',
    help='öffnet Upload UI', default=False)

    parser.add_argument('-s', '--setup', dest='setup',
    nargs='?', const=True, metavar='',
    help='öffnet Einstellungen', default=False)

    parser.add_argument('-f', '--forceUpdate', dest='forceUpdate',
    nargs='?', const=True, metavar='',
    help='erzwingt einen Download der LMS infos', default=False)

    args = parser.parse_args()
    return args

#UIs ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def UserInfo():
    print('\nsihw Config')
    print('\tum Aufgaben abzugeben standartisiert abzugeben brauche ich'
    + 'deinen Vor- und Nachname')
    while True:
        vorname = input('\tVorname: ')
        nachname = input('\tNachname: ')
        if pyip.inputYesNo('\tSind sie sicher Y/N ') == 'yes':
            break
    return vorname, nachname


def updateTimer(lastUpdate, intervall):
    if time() - lastUpdate >= intervall:
        if pyip.inputYesNo('Sie sind nicht auf dem letzten Stand updaten Y/N ') == 'yes':
            return True
    return False

def LmsLoginInfo():
    print('\n Login Config: ')
    print('\t Bitte LMS Username und Passwort eingeben')
    while True:
        username = input('\t Username: ')
        password = input('\t Passwort: ')
        if pyip.inputYesNo('\t Sind sie sicher Y/N ') == 'yes':
            break
    return username, password

def setUpdateIntervall(updateIntervall):
    print(' ')
    print('updateIntervall ändern  - Momentanes UpdateIntervall:', updateIntervall, 's')
    while True:
        new = int(pyip.inputInt('\tNeues Intervall in Sekunden: '))
        confirmed = pyip.inputYesNo('\tConfirm Y/N ')
        if confirmed == 'yes':
           break
    print(' ')
    return new

def getFachAufgabeUI(lms):
    while True:
        while True:
            fach = input('Kurs: ')
            possKurse = []
            for _, Kurs in lms['Kurse'].items():
                if fach.lower() in Kurs['title'].lower():
                    possKurse.append(Kurs)

            if len(possKurse) > 1:
                print('\nIch habe folgende gefunden welchen meinst du')

                for i, Kurs in enumerate(possKurse):
                    print('\t' + str(i) + '\t' + Kurs['title'])

                auswahl = int(pyip.inputInt('Kurs: '))

                if auswahl < len(possKurse):
                    Kurs = possKurse[auswahl]
                    break

            if len(possKurse) == 1:
                Kurs = possKurse[0]
                break

        if len(Kurs['aufgaben']) == 0:
            print('Dieser Kurs hat keine Aufgaben\n')
            continue
        if len(Kurs['aufgaben']) > 1:
            print('Es gibt mehr als eine Aufgabe: ')
            for i, aufgabe in enumerate(Kurs['aufgaben']):
                print(i, "\t", aufgabe['title'])
            while True:
                auswahl = int(pyip.inputInt('Aufgabe: '))
                if auswahl < len(Kurs['aufgaben']):
                    aufgabe = Kurs['aufgaben'][auswahl]
                    break
        else:
            aufgabe = Kurs['aufgaben'][0]

        downloadFolder = aufgabe['folder'] if aufgabe['folder'] != None else'C:/Users/%USERNAME%/Downloads/'

        return Kurs, aufgabe, downloadFolder

def setWorkFolder():
    print('\nsihw Config')
    print('\tBitte gib deinen Arbeitsordner an\n')
    while True:
        workFolder = input('\tArbeitsordner: ')
        if pyip.inputYesNo('\tSind sie sicher Y/N ') == 'yes':
            break
    return workFolder

def setupUI(lms):
    print('Dein sihw Setup - was möchtest du tun')
    print('0\tLMS Login Daten')
    print('1\tNamen')
    print('2\tUpdate Intervall')
    print('3\tDeinen Arbeitsordner')
    print('4\tEinen Kurs umbenenen')
    print('5\tNichts')
    auswahl = int(pyip.inputInt('\nBitte gebe die nummer an: '))
    if auswahl == 0:
        lms['username'], lms['password'] = LmsLoginInfo()
    elif auswahl == 1:
        lms['vorname'], lms['nachname'] = UserInfo()
    elif auswahl == 2:
        lms['updateIntervall'] = setUpdateIntervall(lms['updateIntervall'])
    elif auswahl == 3:
        lms['workFolder'] = setWorkFolder()
    elif auswahl == 4:
        changeKursTitleUI(lms)

def changeKursTitleUI(lms):
    changeDict = {}
    print('Welchen denn?')
    for i, (_, Kurs) in enumerate(lms['Kurse'].items()):
        print('\t' + str(i) + '\t' + Kurs['title'])
        changeDict[str(i)] = Kurs['title']
    print(str(len(lms['Kurse'])) + '\t' + 'Gar keinen')
    auswahl = pyip.inputInt('Kurs: ')
    if auswahl < len(lms['Kurse']):
        print('Und zu was: ')
        while True:
            neuerName = input('\tneuer Name: ')
            if pyip.inputYesNo('\tSicher Y/N ') == 'yes':
                break

        for i, (_, Kurs) in enumerate(lms['Kurse'].items()):
            if i == auswahl:
                Kurs['title'] = neuerName

#Formatier Zeug ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def formatHwTableToLmsKurse(table, lms): #html table als input
    titleFromRow = lambda row : row.text.split('\n')[0]
    print('Formatiere Table... :)')
    #parsed table nach allen zeilen
    soup = BeautifulSoup(table, 'html.parser')
    rows = soup.find_all('tr')
    #haut alle zeilen raus die schon abgegeben sind oder beendet wurden

    rows = [row for row in rows if
            'closed-homework' not in str(row) and
            'title=\"Abgegeben\"' not in str(row) and
            'class=\"comment\"' not in str(row)
            ]

    i = 0
    while True:
        if i >= len(rows):
            break

        if '<strong>' in str(rows[i]):
            KursTitle = titleFromRow(rows[i])

            if lms['Kurse'] == None:
                lms['Kurse'] = {
                    KursTitle : {
                        'title' : KursTitle,
                        'library' : None,
                        'aufgaben' : []
                    }
                }

            if KursTitle not in lms['Kurse']:
                lms['Kurse'][KursTitle] = {
                    'title' : KursTitle,
                    'library' : None,
                    'aufgaben' : []
                }

            currentKurs = lms['Kurse'][KursTitle]
            neueAufgaben = []

            while True:
                i += 1
                if i >= len(rows) or '<strong>' in str(rows[i]):
                    break
                tds = rows[i].find_all('td')

                title = tds[1].text
                datum = tds[0].text
                href = tds[1].find('a')
                if href is not None:
                    href = href.get('href')

                isDatum = lambda datum : sum([c.isnumeric() for c in datum]) > 0
                if isDatum(datum):
                    newAufgabe = {
                        'title' : title,
                        'datum' : datum,
                        'href' : href,
                        'info' : None,
                        'folder' : None
                    }

                    for oldAufgabe in currentKurs['aufgaben']:
                        if oldAufgabe['title'] == newAufgabe['title']:
                            newAufgabe['folder'] = oldAufgabe['folder']

                    neueAufgaben.append(newAufgabe)

            currentKurs['aufgaben'] = neueAufgaben

        else:
            i += 1
    return lms

def formatKurseToOutput(Kurse):
    output = '\nAUSSTEHENDE - AUFGABEN\n'
    #stellt fest was der längste Name ist um Tabelle danach auszurichten
    len_of_titles = [len(aufgabe['title']) for _, Kurs in Kurse.items() for aufgabe in Kurs['aufgaben']]
    if not len_of_titles:
        len_of_titles = [0]
    # spacing = max([len(aufgabe['title']) for _, Kurs in Kurse.items() for aufgabe in Kurs['aufgaben']]) + 7 
    spacing = max(len_of_titles) + 5
    for _, Kurs in Kurse.items():
        if len(Kurs['aufgaben']) > 0:
            output += '\t' +Kurs['title']
            for aufgabe in Kurs['aufgaben']:
                output += '\n\t\t' + aufgabe['title'] + ' '*(spacing - len(aufgabe['title']))
                output += aufgabe['datum']
            output += '\n'
    return output

def formatAufgabenInfoToOutput(fach, aufgabe):
    output = '\n'
    output += fach['title'] + '\t' +aufgabe['title'] + '\t' + aufgabe['datum'] + '\n'
    #druckt beschreibung oder eine Fehlermeldung falls er sie nicht findet
    if aufgabe['info'] != None:
        output += '\tBeschreibung:'
        if aufgabe['info']['beschreibung'] == '':
            output += '\t--Keine Beschreibung vorhanden--'
        else:
            #splittet die dinger an den \n und ersetzt durch \t\n um es korrekt einzurücken
            for absatz in aufgabe['info']['beschreibung'].split('\n'):
                output += '\n\t' + absatz
    #falls es dowonload bare Dinger gibt
        if len(aufgabe['info']['downloads']) > 0:
            output += '\n\n\tDownloads:\n '
            #druckt er jedes davon eingerückt
            for link in aufgabe['info']['downloads']:
                output += '\t' + link
    else:
        output += '\n\t--es sieht so aus als wäre noch keine näheren Details bekannt--\n'

    output += '\n'
    return output

#Handler --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def downloadLmsInfoHandler(driver, lms):
    table = DownloadHomeWorkTable(driver)
    lms = formatHwTableToLmsKurse(table, lms)

    for KursTitle in lms['Kurse']:
        Kurs = lms['Kurse'][KursTitle]
        for aufgabe in Kurs['aufgaben']:
            aufgabe['info'] = downloadInfo(driver, aufgabe)

def shoutGenerelleInfos(lms):
    output = formatKurseToOutput(lms['Kurse'])
    print(output)

def shoutSpecificInfo(fach, aufgabe):
    output = formatAufgabenInfoToOutput(fach, aufgabe)
    print(output)

def createHandler(lms, Kurs, aufgabe):
    dirName = Kurs['title'] + '_' + aufgabe['title'] + '_' + lms['vorname'] + lms['nachname']
    dirName = dirName + '\\'
    #remove alles was nicht so geil ist für namensgebung
    replacers = [('ä', 'ü'), ('ö', 'oe'), ('ü', 'ue'), ('?', ''), (':', ''), (' ', ''), ('@', ''), ('/', ''), ('}', ''), ('=', ''), ('\"', ''),
    ('?', ''), ('{', ''), ('|', ''), ('*', ''), ('&', ''), ('`', ''), ('´', ''), ('\'', ''), ('!', ''), ('<', ''), ('>', ''), ('%', ''), ('+', ''),
    ('$', ''), ('#', ''), ]
    for char in replacers:
        dirName = dirName.replace(char[0], char[1])
    dirName = lms['workFolder'] + dirName
    print('Erstellt:', dirName)
    try:
        os.mkdir(dirName)
        aufgabe['folder'] = dirName
    except:
        print('Error accured directory probably already exists')
        print('otherwise check -s (settings) Arbeitsordner')


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, _, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))
            print('Zipping file: ' + str(file))

@contextmanager
def zipManager(new):
    zipf = zipfile.ZipFile(new, 'w', zipfile.ZIP_DEFLATED)
    try:
        yield zipf
    finally:
        zipf.close()

def uploadHandler(driver, Kurs, aufgabe, lms):
    if aufgabe['folder'] == None:
        print('--Kein Hü-Folder gefunden--')
        return
    while True:
        antwort = pyip.inputYesNo('Bist du dir sicher das du ' + aufgabe['title'] + ' abgeben möchtest? Y/N ')
        if antwort == 'yes':
            try:
                folderName = aufgabe['folder'].split('\\')[::-1][1]
                currentDir = os.getcwd() + '\\' + folderName + '\\'
                shutil.copytree(aufgabe['folder'], currentDir)
                #check beim Nächsten mal
                # zipf = zipfile.ZipFile(currentDir[:-1] + '.zip', 'w', zipfile.ZIP_DEFLATED)
                # zipdir(folderName, zipf)
                with zipManager(currentDir[:-1] + '.zip') as zipf:
                    zipdir(folderName, zipf)
                    shutil.rmtree(currentDir)
                # shutil.rmtree(currentDir)
                # zipf.close()

                uploadData = currentDir[:-1] + '.zip'
                _ = uploadFile(driver, uploadData, aufgabe)
                os.remove(uploadData)
                # lms['lastUpdate'] = 0
            except:
                print('Ein Fehler ist aufgetreten, kontorliere ob es diesen ordner wirklich gibt: ')
                print('\t' + aufgabe['folder'])
                break
            break
        else:
            break
    return
#Main Prozesse ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def main():
    with lmsManager() as lms:
        args = initArgs()
        if args.setup:
            setupUI(lms)
        downloadFolder = 'C:/Users/%USERNAME%/Downloads'
        if args.download or args.info or args.upload or args.create:
            fach, aufgabe, downloadFolder = getFachAufgabeUI(lms)
            if args.create:
                createHandler(lms, fach, aufgabe)
                downloadFolder = aufgabe['folder']

        driverFlow = [
            lms['Kurse'] == None or
            args.forceUpdate or
            updateTimer(lms['lastUpdate'], lms['updateIntervall']),

#initialisiert Driver wenn er was downloaden muss, entweder wenn -d oder wenn -c und es download files gibt
            args.download or (args.create and len(aufgabe['info']['downloads']) > 0),
            args.upload
        ]

        if sum(driverFlow) > 0:
            with driverManager(lms['username'], lms['password'], downloadFolder) as driver:
                if driverFlow[0]:
                    downloadLmsInfoHandler(driver, lms)
                    lms['lastUpdate'] = time()
                if driverFlow[1]:
                    downloadFiles(driver, aufgabe)
                if driverFlow[2]:
                    uploadHandler(driver, fach, aufgabe, lms)
                    downloadLmsInfoHandler(driver, lms)

        if args.info:
            shoutSpecificInfo(fach, aufgabe)
        elif sum([args.info, args.download, args.upload, args.create, args.setup]) == 0:
            shoutGenerelleInfos(lms)
if __name__ == '__main__':
    main()

#Flags
# no flag gibt generelle info aus
#-i öffnet info UI
#-d öffnet downlaod UI
#-c öffnet create UI
#-u öffnet upload UI
#-s öffnet setup ui
#-f erzwingt update


# lms = {
#     'username':'email@email.com',
#     'password':'Som3Passwörd!',
#     'vorname':'Ben',
#     'nachname':'Wernicke',
#     'updateIntervall':7200,
#     'lastUpdate':time(),
#       'workFolder',
#     'Kurse':{
#         '8Kl Ma':{
#             'title':'Mathe', #vom User gesetzt -> Default LMS Kurstitel
#             'lib':'link to LMS libra',:
#             'aufgaben':[ #liste aus dicts eines für jede aufgabe
#                 {
#                     'title':'Buch Seite 3...',
#                     'datum':'Mo 13.12.2020', #abgabedatum
#                     'href':'https://lms.at/...', #link zu aufgabe
#                     'folder':'C:/Users...', #Ordner für Aufgabenausarbeitung w
#                     #wird von sihw erstellt, wenn nicht erstellt None
#                     'info': { #ist None falls es keine gibt
#                         'beschreibung':'Das ist eine Beschriebung',
#                         'downloads':['NameDesFiles.pdf']
#                     }
#                 }
#             ],
#         }
#     }
# }
