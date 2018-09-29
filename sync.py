#!/usr/bin/env python3

### IMPORTS ###
import os
import shutil
import glob
import json
import time
from argparse import ArgumentParser
# needs imagemagick, pdftk

# Set Parameters and folders for sync
syncDirectory="/Users/lisa/Documents/Literature"
remarkableBackupDirectory="/Users/lisa/Documents/remarkableBackup"
remContent="/xochitl"
remarkableDirectory="/home/root/.local/share/remarkable/xochitl"
remarkableUsername="root"
remarkableIP = "10.11.99.1"
# https://github.com/lschwetlick/maxio/tree/master/tools
conversionScriptPDF="/Users/lisa/Documents/Projects/rMTools/maxio/tools/rM2pdf"
conversionScriptNotes="/Users/lisa/Documents/Projects/rMTools/maxio/tools/rM2svg"
# https://github.com/reHackable/scripts
pushScript="/Users/lisa/Documents/Projects/rMTools/scripts/host/repush.sh"

def main():
    parser = ArgumentParser()
    parser.add_argument("-b",
                        "--backup",
                        help="pass when rM is connected, to back up rM data",
                        action='store_true',
                        )
    parser.add_argument("-c",
                        "--convert",
                        help="use rM files in backup directory to generate annotated PDFs and save them in your library",
                        action='store_true',
                        )
    parser.add_argument("-u",
                        "--upload",
                        help="upload new files in library to rM",
                        action='store_true',
                        )
    parser.add_argument("-d",
                        "--dry_upload",
                        help="just print upload commands",
                        action='store_true',
                        )
    args = parser.parse_args()
    if args.backup:
        backupRM()
    if args.convert:
        convertFiles()
    if args.upload:
        print("upload")
        uploadToRM_curl(args.dry_upload)
    print("Done!")

### BACK UP ###
# TODO: catch connection errors
# TODO: only backup changed files (Problem is that rM doesnt run rsync)
def backupRM():
    print("Backing up your remarkable files")
    #Sometimes the remarkable doesnt connect properly. In that case turn off & disconnect -> turn on -> reconnect
    backupCommand="".join(["scp -r ",remarkableUsername,"@",remarkableIP,":",remarkableDirectory," ", remarkableBackupDirectory])
    os.system(backupCommand)
    # os.system("scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl /Users/lisa/Documents/remarkableBackup")


### CONVERT TO PDF ###
# TODO: underlay notebook templates?
def convertFiles():
    #### Get file lists
    # syncFilesList=glob.glob(syncDirectory+"/*/*.pdf")
    rmPdfList=glob.glob(remarkableBackupDirectory+remContent+"/*.pdf")
    rmLinesList=glob.glob(remarkableBackupDirectory+remContent+"/*.lines")
    # notesList=[ os.path.basename(f) for f in rmLinesList ] # in the loop we remove all that have an associated pdf

    for i in range(0,len(rmLinesList)):
        # get file reference number
        refNr=os.path.basename(rmLinesList[i][:-6])
        refNrPath= rmLinesList[i][:-6]

        # get meta Data
        meta= json.loads(open(refNrPath+".metadata").read())
        # Make record of pdf files already on device
        # pdfNamesOnRm.append(meta["visibleName"]+".pdf")

        # Does this lines file have an associated pdf?
        AnnotPDF = True if refNrPath+".pdf" in rmPdfList else False

        if AnnotPDF:
            # deal with annotated pdfs
            syncFilePath= syncDirectory+"/*/"+meta["visibleName"]+".pdf" if meta["visibleName"][-4:]!=".pdf" else syncDirectory+"/*/"+meta["visibleName"]
            inSyncFolder= True if glob.glob(syncFilePath)!=[] else False
            if inSyncFolder:
                origPDF=glob.glob(syncFilePath)[0]
                subFolder=os.path.basename(os.path.dirname(origPDF))
                # export
                print(meta["visibleName"]+" is being exported.")

                linesOut= syncDirectory+"/"+subFolder+"/"+"lines_temp.pdf"
                # could also use empty pdf on remarkable, but computer side annotations are lost. this way if something has been annotated lots fo times it may stat to suck in quality
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


### UPLOAD ###
# TODO: Upload to folders (scripts/repush.sh)
def uploadToRM(dry):
    # list of files in Library
    syncFilesList=glob.glob(syncDirectory+"/*/*.pdf")
    # list of files on the rM (hashed)
    rmPdfList=glob.glob(remarkableBackupDirectory+remContent+"/*.pdf")
    # make list of actual names (not hashed)
    pdfNamesOnRm=[]
    for i in range(0,len(rmPdfList)):
        refNrPath= rmPdfList[i][:-4]
        # get meta Data
        meta= json.loads(open(refNrPath+".metadata").read())
        # Make record of pdf files already on device
        rmPdfName= meta["visibleName"]+".pdf" if meta["visibleName"][-4:]!=".pdf" else meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)
    
    # remove files in the Notes directory from the list (those dont need to be re-uploaded)
    syncFilesList= [ x for x in syncFilesList if "/Notes/" not in x ]
    # find absolute path
    syncNames = [ os.path.basename(f) for f in syncFilesList ]
    # remove annotated pdf files from the list (those dont need to be re-uploaded)
    syncNames= [ x for x in syncNames if "annot" not in x ]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]
    # print("uploadList:")
    # print(uploadList)

    uploadPathList= [glob.glob(syncDirectory+"/*/"+x)[0] for x in uploadList]
    # print("uploadPathList:")
    # print(uploadPathList)
    # do in batches of the folders
    folderList = [os.path.dirname(x).split('/')[-1] for x in uploadPathList]
    # print(folderList)
    batches= list(set(folderList))

    # print(batches)

    for folder in batches:
        filesInFolder=[f for f in uploadPathList if folder == os.path.dirname(f).split('/')[-1]]
        print("upload "+ " ".join(filesInFolder) +" to "+folder)

        folderpath=os.path.dirname(filesInFolder[0])
        if folderpath != syncDirectory:
            uploadCmd="".join(["bash ", pushScript, " -o /", folder," "," ".join(filesInFolder)])
        else:
            uploadCmd="".join(["bash ", pushScript, " ".join(filesInFolder)])

        if dry:
            print('uploadCmd: ')
            print(uploadCmd)
        else:
            os.system(uploadCmd)
            #Sleep to allow restart
            print('sleeping while rM restarts')
            time.sleep(15)




def uploadToRM_curl(dry):
        # list of files in Library
    syncFilesList=glob.glob(syncDirectory+"/*/*.pdf")
    # list of files on the rM (hashed)
    rmPdfList=glob.glob(remarkableBackupDirectory+remContent+"/*.pdf")
    # make list of actual names (not hashed)
    pdfNamesOnRm=[]
    for i in range(0,len(rmPdfList)):
        refNrPath= rmPdfList[i][:-4]
        # get meta Data
        meta= json.loads(open(refNrPath+".metadata").read())
        # Make record of pdf files already on device
        rmPdfName= meta["visibleName"]+".pdf" if meta["visibleName"][-4:]!=".pdf" else meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)
    
    # remove files in the Notes directory from the list (those dont need to be re-uploaded)
    syncFilesList= [ x for x in syncFilesList if "/Notes/" not in x ]
    # find absolute path
    syncNames = [ os.path.basename(f) for f in syncFilesList ]
    # remove annotated pdf files from the list (those dont need to be re-uploaded)
    syncNames= [ x for x in syncNames if "annot" not in x ]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]

    for i in range(0,len(uploadList)):
        # get full path for the file to be uploaded
        filePath=glob.glob(syncDirectory+"/*/"+uploadList[i])[0]
        # chop the ending if necessary to get file name
        fileName=uploadList[i] if uploadList[i][-4:0]!="pdf" else uploadList[:-4]

        print("upload "+ fileName +" from "+filePath)

        # # CURL version (can't copy directly to folders)
        # #http://remarkablewiki.com/index.php?title=Methods_of_access
        # #chronos@localhost ~/Downloads $ curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@Get_started_with_reMarkable.pdf;filename=Get_started_with_reMarkable.pdf;type=application/pdf" 
        uploadCmd="".join(["curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F 'file=@",filePath,";filename=",fileName,";type=application/pdf'"])
        os.system(uploadCmd)
        # folderpath=os.path.dirname(filePath)
        # if folderpath != syncDirectory:
        #     foldername=folderpath.split('/')[-1]
        #     uploadCmd="".join(["bash ", pushScript, " -o /", foldername," ",filePath])
        # else:
        #     uploadCmd="".join(["bash ", pushScript, filePath])

        if dry:
            print('uploadCmd: ')
            print(uploadCmd)
        else:
            os.system(uploadCmd)
            # time.sleep(10)





if __name__ == "__main__":
    main()