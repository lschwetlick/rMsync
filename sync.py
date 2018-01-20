import os
import shutil
import glob
import json
import numpy as np
# needs imagemagick, pdftk

# Set Parameters for sync
syncDirectory="/Users/lisa/Documents/Literature"
remarkableBackupDirectory="/Users/lisa/Documents/remarkableBackup"
remContent="/xochitl"
remarkableDirectory="/home/root/.local/share/remarkable/xochitl"
remarkableUsername="root"
remarkableIP="10.11.99.1"
remarkablePassword="AyzZl13kOs"
conversionScriptPDF="/Users/lisa/Documents/rMTools/maxio/tools/rM2svg"
conversionScriptNotes="/Users/lisa/Documents/rMTools/orinalMaxio/maxio/tools/rM2svg"


#### Back up Files from reMarkable
sync = input("Do you want to Sync from your rM? (y/n)")
if sync=="y":
    print("Backing up your remarkable files")
    #Sometimes the remarkable doesnt connect properly. In that case turn off & disconnect -> turn on -> reconnect
    backupCommand="".join(["scp -r ",remarkableUsername,"@",remarkableIP,":",remarkableDirectory," ", remarkableBackupDirectory])
    os.system(backupCommand)
    # os.system("scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl /Users/lisa/Documents/remarkableBackup") 

#### Get file lists
syncFilesList=glob.glob(syncDirectory+"/*/*.pdf")
rmPdfList=glob.glob(remarkableBackupDirectory+remContent+"/*.pdf")
rmLinesList=glob.glob(remarkableBackupDirectory+remContent+"/*.lines")
# notesList=[ os.path.basename(f) for f in rmLinesList ] # in the loop we remove all that have an associated pdf


# #Later ToDo: find standalone notes files and put those somewhere seperate

for i in range(0,len(rmLinesList)):
    # get file reference number
    refNr=os.path.basename(rmLinesList[i][:-6])
    refNrPath= rmLinesList[i][:-6]
    # get meta Data
    meta= json.loads(open(refNrPath+".metadata").read())
    # Make record of pdf files already on device
    # pdfNamesOnRm.append(meta["visibleName"]+".pdf")
    # Do we need to Copy this file from the rM to the computer?
    AnnotPDF= True if refNrPath+".pdf" in rmPdfList else False

    if AnnotPDF:
        # deal with annotated pdfs
        inSyncFolder= True if glob.glob(syncDirectory+"/*/"+meta["visibleName"]+".pdf")!=[] else False
        if inSyncFolder:
            origPDF=glob.glob(syncDirectory+"/*/"+meta["visibleName"]+".pdf")[0]
            subFolder=os.path.basename(os.path.dirname(origPDF))
            # export
            print(meta["visibleName"]+" is being exported.")


            linesOut= syncDirectory+"/"+subFolder+"/"+"lines_temp.pdf"
            # could also use empty pdf on remarkable, but computer side annotations are lost. this way if something has been annotated lots fo times it may stat to suck in quality
            # uses github code
            convertlinesCmd="".join(["python3 ",conversionScriptPDF," -i ",refNrPath,".lines", " -p ",origPDF," -o ", linesOut])
            # print(convertlinesCmd)
            os.system(convertlinesCmd)
            # stamp extracted lines onto original with pdftk
            stampCmd="".join(["pdftk ", origPDF, " multistamp ", linesOut, " output ", origPDF[:-4],"_annot.pdf"])
            os.system(stampCmd)
            # Remove temporary files
            os.remove(linesOut)


        else:
            print(meta["visibleName"]+" does not exist in the sync directory")
            # ToDo allow y/n input whether it should be copied there anyway
    else:
        # deal with blank notes
        # needs imagemagick
        print("exporting Notebook " + meta["visibleName"])
        # print(refNrPath)


        noteOut=syncDirectory+"/Notes"+meta["visibleName"]
        svgOut="/Users/lisa/Documents/Literature/Notes/tmp/note.svg"
        # make temp directory
        os.system("mkdir "+syncDirectory+"/Notes/tmp")
        # Convert lines to svgs
        convertlinSvgCmd="".join(["python3 ",conversionScriptNotes," -i ",refNrPath,".lines", " -o ",svgOut])
        os.system(convertlinSvgCmd)
        # Convert svgs to a pdf
        convertSvg2PdfCmd="".join(["convert -density 100 ", svgOut[:-4],"_*.svg", " -transparent white ", "/Users/lisa/Documents/Literature/Notes/",meta["visibleName"].replace(" ", "_"),".pdf"])
        os.system(convertSvg2PdfCmd)
        # Delete temp directory
        shutil.rmtree(syncDirectory+"/Notes/tmp/", ignore_errors=False, onerror=None)
pdfNamesOnRm=[]
for i in range(0,len(rmPdfList)):
    refNrPath= rmPdfList[i][:-4]
    # get meta Data
    meta= json.loads(open(refNrPath+".metadata").read())
    # Make record of pdf files already on device
    pdfNamesOnRm.append(meta["visibleName"]+".pdf")


### UPLOAD ###
# we dont want to re-upload Notes
syncFilesList= [ x for x in syncFilesList if "/Notes/" not in x ]
# print("syncFilesList")
# print(syncFilesList)

syncNames = [ os.path.basename(f) for f in syncFilesList ]
# we dont want to re-upload annotated pdfs
syncNames= [ x for x in syncNames if "annot" not in x ]

# print("syncNames")
# print(syncNames)


# this gets elements that are in list 1 but not in list 2
uploadList = np.setdiff1d(syncNames,pdfNamesOnRm)
# print("pdfNamesOnRm")
# print(pdfNamesOnRm)
# print("uploadList")
# print(uploadList)

for i in range(0,len(uploadList)):
    filePath=glob.glob(syncDirectory+"/*/"+uploadList[i])[0]
#     # ToDo
#     #http://remarkablewiki.com/index.php?title=Methods_of_access
    print("upload "+ uploadList[i])
    uploadCmd="".join(["curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F 'file=@",filePath,";filename=",uploadList[i],";type=application/pdf'"])
    os.system(uploadCmd)

#     #chronos@localhost ~/Downloads $ curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@Get_started_with_reMarkable.pdf;filename=Get_started_with_reMarkable.pdf;type=application/pdf" 
#     # Upload successfullchronos@localhost ~/Downloads $
#     print("upload "+ uploadList[i])
