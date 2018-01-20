import os
import glob
# import re
import json
import numpy as np

# Set Parameters for sync
syncDirectory="/Users/lisa/Documents/Literature/Papers"
remarkableBackupDirectory="/Users/lisa/Documents/remarkableBackup"
remContent="/xochitl"
remarkableDirectory="/home/root/.local/share/remarkable/xochitl"
remarkableUsername="root"
remarkableIP="10.11.99.1"
remarkablePassword="AyzZl13kOs"
conversionSkript="/Users/lisa/Documents/rMTools/maxio/tools/rM2svg"

#Sometimes the remarkable doesnt connect properly. In that case turn off & disconnect -> turn on -> reconnect
backupCommand="".join(["scp -r ",remarkableUsername,"@",remarkableIP,":",remarkableDirectory," ", remarkableBackupDirectory])
os.system(backupCommand)
# os.system("scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl /Users/lisa/Documents/remarkableBackup") 
print("Backing up your remarkable files")

# os.chdir('~')
syncFilesList=glob.glob(syncDirectory+"/*.pdf")
rmPdfList=glob.glob(remarkableBackupDirectory+remContent+"/*.pdf")
rmLinesList=glob.glob(remarkableBackupDirectory+remContent+"/*.lines")
notesList=[ os.path.basename(f) for f in rmLinesList ] # in the loop we remove all that have an associated pdf

print(rmLinesList)
# #Later ToDo: find standalone notes files and put those somewhere seperate
pdfNamesOnRm=[]
for i in range(0,len(rmPdfList)):
    refNrPath=rmPdfList[i][:-4]
    refNr=os.path.basename(refNrPath[:-4])
    # if remove if associated pdf exists
    notesList.remove(refNr+".lines")
    # Get metadata from meta file
    meta= json.loads(open(refNrPath+".metadata").read())
    # Make record of pdf files already on device
    pdfNamesOnRm.append(meta["visibleName"]+".pdf")
    # Do we need to Copy this file from the rM to the computer?
    edited= True if refNrPath+".lines" in rmLinesList else False
    inSyncFolder= True if glob.glob(syncDirectory+"/"+meta["visibleName"]+".pdf")!=[] else False
    if edited & inSyncFolder:
        # ToDo
        print(meta["visibleName"]+" is being exported.")
        origPDF=syncDirectory+"/"+meta["visibleName"]+".pdf"
        linesOut= syncDirectory+"/"+"lines_temp.pdf"
        # could also use empty pdf on remarkable, but computer side annotations are lost. this way if something has been annotated lots fo times it may stat to suck in quality
        # uses github code
        convertlinesCmd="".join(["python3 ",conversionSkript," -i ",refNrPath,".lines", " -p ",origPDF," -o ", linesOut])
        os.system(convertlinesCmd)
        # stamp extracted lines onto original with pdftk
        stampCmd="".join(["pdftk ", origPDF, " multistamp ", linesOut, " output ", origPDF[:-4],"_annot.pdf"])
        os.system(stampCmd)
        # Remove temporary files
        os.remove(linesOut)
    else:
        print(" ".join(["Name:",meta["visibleName"],"edited:",str(edited),"inSyncFolder:",str(inSyncFolder)]))

syncNames = [ os.path.basename(f) for f in syncFilesList ]
# this gets elements that are in list 1 but not in list 2
uploadList = np.setdiff1d(syncNames,pdfNamesOnRm)

for i in range(0,len(uploadList)):
    filePath=syncDirectory+"/"+uploadList[i]
    # ToDo
    #http://remarkablewiki.com/index.php?title=Methods_of_access
    #chronos@localhost ~/Downloads $ curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@Get_started_with_reMarkable.pdf;filename=Get_started_with_reMarkable.pdf;type=application/pdf" 
    # Upload successfullchronos@localhost ~/Downloads $
    print("upload "+ uploadList[i])
