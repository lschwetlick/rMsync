"""
Commandline Utility to Backup, Convert and Upload files from the remarkable
"""
#!/usr/bin/env python3

### IMPORTS ###
import os
import sys
import shutil
import glob
import json
import time
import warnings
from argparse import ArgumentParser
#from PyPDF2 import PdfFileReader
import pikepdf
from rm_tools.rM2svg import rm2svg
# needs imagemagick, pdftk

__prog_name__ = "sync"

# Set Parameters and folders for sync
# this folder has all the pdfs that need to be synced
syncDirectory = "/Users/lisa/Documents/Literature"
# The folder where notes will be exported to (it is excluded from the uploading)
notesDirectory = "Notes"
# Basic set up
remarkableBackupDirectory = "/Users/lisa/Documents/remarkableBackup"
remContent = "xochitl"
remarkableDirectory = "/home/root/.local/share/remarkable/xochitl"
remarkableUsername = "root"
remarkableIP = "10.11.99.1" #"192.168.0.87"# "10.11.99.1"

# This is a script that supposedly uploads multiple files at a time
pushScript = "/Users/lisa/Documents/Projects/rMTools/scripts/host/repush.sh"
# This folder contains all the notbook backgrounds the remarkable has
# (and that I have added). Lives at "/usr/share/remarkable/templates/" on the RM
bgPath = "/Users/lisa/Documents/remarkableBackup/templates/"
# This is an empty rm file
emptyRm = "/Users/lisa/Documents/remarkableBackup/empty.rm"

def main():
    """
    Parse Commandline Arguments
    """
    parser = ArgumentParser()
    parser.add_argument("-b",
                        "--backup",
                        help="pass when rM is connected, to back up rM data",
                        action="store_true")
    parser.add_argument("-c",
                        "--convert",
                        help="use rM files in backup directory to generate "
                             "annotated PDFs and save them in your library",
                        action="store_true")
    parser.add_argument("-u",
                        "--upload",
                        help="upload new files in library to rM",
                        action="store_true")
    parser.add_argument("-d",
                        "--dry_upload",
                        help="just print upload commands",
                        action="store_true")
    parser.add_argument("-p",
                        "--purge",
                        help="Deletes local backup folder before backing"
                             "up",
                        action="store_true")
    parser.add_argument("-s",
                        "--single",
                        help="Uploads a single file",
                        action="store")
    parser.add_argument("-v",
                        "--verbose",
                        help="prints info about exactly what is happening",
                        action="store_true")
    parser.add_argument("-f",
                        "--conv_one",
                        help="Finds and Converts a single file",
                        action="store")

    args = parser.parse_args()
    if args.single:
        uploadSingleFile(args.single, args.dry_upload)
        if args.backup or args.convert or args.upload:
            print("Uploaded single file. Please run separate command for " +
                  "other tasks.")
        return(True)
    if args.conv_one:
        findAndConvert(args.conv_one, verbose=args.verbose)
        if args.backup or args.convert or args.upload:
            print("Converted single file. Please run separate command for " +
                  "other tasks.")
        return(True)

    if args.backup:
        backupRM(purge=args.purge, verbose=args.verbose)
    if args.convert:
        convertFiles(verbose=args.verbose)
    if args.upload:
        print("upload")
        uploadToRM_curl(args.dry_upload, verbose=args.verbose)
    print("Done!")

### BACK UP ###
def backupRM(purge=False, verbose=False):
    """
    Backs up all files on the remarkable so we can then convert them.
    Also its always nice to have a backup. Downside is that it kaes a while
    because rsync doesn't work and we are copying EVERYTHING!

    Sometimes the remarkable doesnt connect properly. In that case turn off &
    disconnect -> turn on -> reconnect. It also extremely sensitive to cables.

    """
    print("Backing up your remarkable files")
    if purge:
        shutil.rmtree("/Users/lisa/Documents/remarkableBackup/" + remContent)
        print("deleted old files")
    backupCommand = "".join(["scp -r ", remarkableUsername, "@", remarkableIP,
                             ":", remarkableDirectory, " ",
                             remarkableBackupDirectory])
    if verbose:
        print(f"Doing Backup: {backupCommand}")
    os.system(backupCommand)

### CONVERT TO PDF ###
def convertFiles(verbose=False):
    """
    Converts Files on rM to PDF versions and saves them the the appropriate
    folders. Only converts things that have been changed since the last sync.
    """

    #### Get file lists
    tmp = os.path.join(remarkableBackupDirectory,remContent)
    files = [x for x in os.listdir(tmp) if "." not in x]

    for i in range(0, len(files)):
        # get file reference number
        refNrPath = os.path.join(remarkableBackupDirectory, remContent,
                                 files[i])
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        fname = meta["visibleName"]
        fname = fname.replace(" ", "_")
        # Does this lines file have an associated pdf?
        AnnotPDF = os.path.isfile(refNrPath + ".pdf")
        convertSingleFile(refNrPath, AnnotPDF, meta, fname, verbose=verbose)

def convertSingleFile(refNrPath, AnnotPDF, meta, fname, verbose=False, force=False):
    # Get list of all rm files i.e. all pages
    npages = len(glob.glob(refNrPath + "/*.rm"))
    if npages != 0:
        if AnnotPDF:
            # we have found an annotated pdf
            # now make sure it has the right ending
            if meta["visibleName"][-4:] != ".pdf":
                syncFilePath = os.path.join(syncDirectory, "*",
                                            meta["visibleName"] + ".pdf")
            else:
                syncFilePath = os.path.join(syncDirectory, "*",
                                            meta["visibleName"])

            # does the file exist in our system?
            inSyncFolder = glob.glob(syncFilePath) != []

            if inSyncFolder:
                # have we exported this thing before?
                local_annotExist = \
                    glob.glob(syncFilePath[:-4] + "_annot.pdf") != []
                # first, assume, it needs converting
                remoteChanged = True
                if local_annotExist:
                    # if it already exists check when it was last updated
                    local_annotPath = \
                        glob.glob(syncFilePath[:-4]+"_annot.pdf")[0]
                    local_annot_mod_time = os.path.getmtime(local_annotPath)
                    # rm time is in ms
                    remote_annot_mod_time = int(meta["lastModified"])/1000
                    # has this version changed since we last exported it?
                    remoteChanged = \
                        remote_annot_mod_time > local_annot_mod_time
                # update if the remote version has changed
                if remoteChanged or force:
                    origPDF = glob.glob(syncFilePath)[0]
                    #####
                    if verbose:
                        print(f"I will convert the file with {fname}, {refNrPath}, {origPDF}")
                    convertAnnotatedPDF(fname, refNrPath, origPDF, verbose=verbose)
                    #####
                else:
                    print(fname + " hasn't been modified")
            else:
                print(fname + " does not exist in the sync directory")
                # TODO allow y/n input whether it should be copied there
                # anyway
        else:
            # we found a note
            print("exporting Notebook " + fname)
            syncFilePath = os.path.join(syncDirectory, notesDirectory,
                                    fname + ".pdf")
            inSyncFolder = glob.glob(syncFilePath) != []
            remoteChanged = True
            if inSyncFolder:
                local_annot_mod_time = os.path.getmtime(syncFilePath)
                remote_annot_mod_time = int(meta['lastModified'])/1000
                remoteChanged = remote_annot_mod_time > local_annot_mod_time
            if remoteChanged:
                #####
                convertNotebook(fname, refNrPath, verbose=verbose)
                #####
            else:
                print(fname + "has not changed")



def findAndConvert(file_to_convert, verbose=False, save_to=""):
    """
    Find and covert  a single file
    """
    name_dict = makeNameDict()
    if file_to_convert not in name_dict.keys():
        print(name_dict.keys())
        raise Exception(f"That file {file_to_convert} does not appear to be there.")
    refNrPath = name_dict[file_to_convert]
    # Does this lines file have an associated pdf?
    AnnotPDF = os.path.isfile(refNrPath + ".pdf")
    meta = json.loads(open(refNrPath + ".metadata").read())
    convertSingleFile(refNrPath, AnnotPDF, meta, file_to_convert, verbose=verbose, force=True)


def makeNameDict():
    """
    Return a dictionary of all files and their reference numbers
    """
    d = {}
    #### Get file lists
    tmp = os.path.join(remarkableBackupDirectory,remContent)
    files = [x for x in os.listdir(tmp) if "." not in x]
    for i in range(0, len(files)):
        # get file reference number
        refNrPath = os.path.join(remarkableBackupDirectory, remContent,
                                 files[i])
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        fname = meta["visibleName"]
        fname = fname.replace(" ", "_")
        d[fname] = refNrPath
    return d


### UPLOAD ###
# TODO: Upload to folders (scripts/repush.sh)
def uploadToRM(dry, verbose=False):
    """
    Uploads files to the rM. This should allow us to set a folder. DOESNT WORK YET!
    """
    # list of files in Library
    syncFilesList = glob.glob(syncDirectory + "/*/*.pdf")
    # list of files on the rM (hashed)
    rmPdfList = glob.glob(remarkableBackupDirectory + remContent + "/*.pdf")
    # make list of actual names (not hashed)
    pdfNamesOnRm = []
    for i in range(0, len(rmPdfList)):
        refNrPath = rmPdfList[i][:-4]
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        # Make record of pdf files already on device
        rmPdfName = meta["visibleName"] + ".pdf" if meta["visibleName"][-4:] != ".pdf" else meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)

    # remove files in the Notes directory from the list (those dont need to be re-uploaded)
    syncFilesList = [x for x in syncFilesList if "/Notes/" not in x]
    # find absolute path
    syncNames = [os.path.basename(f) for f in syncFilesList]
    # remove annotated pdf files from the list (those dont need to be re-uploaded)
    syncNames = [x for x in syncNames if "annot" not in x]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]
    # print("uploadList:")
    # print(uploadList)

    uploadPathList = [glob.glob(syncDirectory + "/*/" + x)[0] for x in uploadList]
    # print("uploadPathList:")
    # print(uploadPathList)
    # do in batches of the folders
    folderList = [os.path.dirname(x).split("/")[-1] for x in uploadPathList]
    # print(folderList)
    batches = list(set(folderList))

    # print(batches)

    for folder in batches:
        filesInFolder = [f for f in uploadPathList if folder == os.path.dirname(f).split("/")[-1]]
        print("upload " + " ".join(filesInFolder) + " to " + folder)

        folderpath = os.path.dirname(filesInFolder[0])
        if folderpath != syncDirectory:
            uploadCmd = "".join(["bash ", pushScript, " -o /", folder, " ", " ".join(filesInFolder)])
        else:
            uploadCmd = "".join(["bash ", pushScript, " ".join(filesInFolder)])

        if dry:
            print("uploadCmd: ")
            print(uploadCmd)
        else:
            if verbose:
                print(f"Doing Upload: f{uploadCmd}")
            os.system(uploadCmd)
            #Sleep to allow restart
            print("sleeping while rM restarts")
            time.sleep(15)




def uploadToRM_curl(dry, verbose):
    """
    Uploads files to the rM. They will land just in the home folder for manual
    sorting. filenames cant have "-" in them!
    """
    # list of files in Library
    syncFilesList = glob.glob(os.path.join(syncDirectory, "*", "*.pdf"))
    # list of files on the rM (hashed)
    rmPdfList = glob.glob(os.path.join(remarkableBackupDirectory, remContent,
                                       "*.pdf"))
    # make list of actual names (not hashed)
    pdfNamesOnRm = []
    for i in range(0, len(rmPdfList)):
        refNrPath = rmPdfList[i][:-4]
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        # Make record of pdf files already on device
        if meta["visibleName"][-4:] != ".pdf":
            rmPdfName = meta["visibleName"] + ".pdf"
        else:
            rmPdfName = meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)
    # remove files in the Notes directory from the list
    # (those dont need to be re-uploaded)
    syncFilesList = [x for x in syncFilesList \
                        if "/" + notesDirectory + "/" not in x]
    # find absolute path
    syncNames = [os.path.basename(f) for f in syncFilesList]
    # remove annotated pdf files from the list
    # (those dont need to be re-uploaded)
    syncNames = [x for x in syncNames if "annot" not in x]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]
    for upl in uploadList:
        # get full path for the file to be uploaded
        filePath = glob.glob(os.path.join(syncDirectory, "*", upl))[0]
        # chop the ending if necessary to get file name
        fileName = upl if upl[-4:0] != "pdf" else upl[:-4]

        print("upload "+ fileName +" from "+filePath)

        # # CURL version (can't copy directly to folders)
        # #http://remarkablewiki.com/index.php?title=Methods_of_access
        # #chronos@localhost ~/Downloads $ curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@Get_started_with_reMarkable.pdf;filename=Get_started_with_reMarkable.pdf;type=application/pdf"
        #uploadCmd = "".join(["curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F 'file=@", filePath, ";filename=", fileName, ";type=application/pdf'"])
        uploadCmd = "".join(["curl 'http://",remarkableIP,"/upload' -H 'Origin: http://",remarkableIP,"' -H 'Accept: */*' -H 'Referer: http://",remarkableIP,"' -H 'Connection: keep-alive' -F 'file=@", filePath, ";filename=", fileName, ";type=application/pdf'"])

        if dry:
            print("uploadCmd: ")
            print(uploadCmd)
        else:
            os.system(uploadCmd)

def uploadSingleFile(filePath, dry=False, verbose=False):
    """
    Uploads one specific file. Useful if you dont want to do a full backup.
    """
    if os.path.isfile(filePath):
        # chop the ending if necessary to get file name
        basename = os.path.basename(filePath)
        fileName = basename if basename[-4:0] != "pdf" else basename[:-4]

        print("upload "+ fileName +" from "+filePath)

        uploadCmd = "".join(["curl 'http://",remarkableIP,"/upload' -H 'Origin: http://",remarkableIP,"' -H 'Accept: */*' -H 'Referer: http://",remarkableIP,"' -H 'Connection: keep-alive' -F 'file=@", filePath, ";filename=", fileName, ";type=application/pdf'"])

        if dry:
            print("uploadCmd: ")
            print(uploadCmd)
        else:
            if verbose:
                print(f"Doing Upload: {uploadCmd}")
            os.system(uploadCmd)
    else:
        warnings.warn("Cant find that file, sorry!")


def convertNotebook(fname, refNrPath, verbose=False):
    """
    Converts Notebook to a PDF by taking the annotations and the template
    background for that notebook.
    """
    #tempdir is where I will save in between files
    try:
        os.mkdir('tempDir')
    except:
        pass
    # get list of backgrounds
    with open(refNrPath+".pagedata") as file:
        backgrounds = [line.strip() for line in file]

    bg_pg = 0
    bglist = []
    for bg in backgrounds:
        convertSvg2PdfCmd = "".join(["rsvg-convert -f pdf -o ", "tempDir/bg_"\
                                     + str(bg_pg) + ".pdf ", str(bgPath)\
                                     + bg.replace(" ", "\ ") + ".svg"])
        if verbose:
            print(f"Doing Convert: {convertSvg2PdfCmd}")
        os.system(convertSvg2PdfCmd)
        bglist.append("tempDir/bg_"+str(bg_pg)+".pdf ")
        bg_pg += 1
    merged_bg = "tempDir/merged_bg.pdf"
    convert_command = "convert " + (" ").join(bglist) + " " + merged_bg
    if verbose:
        print(f"Doing coversion: {convert_command}")
    os.system(convert_command)

    # get info from the pdf we just made
    #input1 = pikepdf.Pdf.open(origPDF)
    #pdfsize = input1.pages[0].trimbox

    # find out the page hashes
    content = json.loads(open(refNrPath + ".content").read())
    # Now convert all Pages
    pdflist = []
    for pg, pg_hash in enumerate(content['pages']):
        if verbose:
            print(f"Page: {pg}")
        rmpath = refNrPath + "/" + pg_hash + ".rm"
        # skip page if it doesnt extist anymore. This is fine in notebooks
        # because nobody cares about the rM numbering.
        try:
            rm2svg(rmpath, "tempDir/temprm" + str(pg) + ".svg",
                   coloured_annotations=True)
            convertSvg2PdfCmd = \
                "".join(["rsvg-convert -f pdf -o ", "tempDir/temppdf" + \
                    str(pg), ".pdf ", "tempDir/temprm" + str(pg) + ".svg"])
            os.system(convertSvg2PdfCmd)
            pdflist.append("tempDir/temppdf"+str(pg)+".pdf")
        except FileNotFoundError:
            continue
    # merge all annotation pages
    merged_rm = "tempDir/merged_rm.pdf"
    mergeCmd = "convert " + (" ").join(pdflist) + " " + merged_rm
    if verbose:
        print(f"Doing Merge: {mergeCmd}")
    os.system(mergeCmd)
    # combine with background
    stampCmd = "".join(["pdftk ", merged_bg, " multistamp ", merged_rm, \
        " output " + syncDirectory + "/Notes/" + fname + ".pdf"])
    if verbose:
        print(f"Doing Stamp: {stampCmd}")
    os.system(stampCmd)
    # Delete temp directory
    shutil.rmtree("tempDir", ignore_errors=False, onerror=None)
    return True

def convertAnnotatedPDF(fname, refNrPath, origPDF, verbose=False):
    """
    Converts a PDF and it's annotations into one PDF.
    """
    #tempdir is where I will save in between files
    try:
        os.mkdir("tempDir")
    except:
        pass
    print(fname+" is being exported.")

    # get info on origin pdf
    try:
        input1 = pikepdf.Pdf.open(origPDF)
        #input1 = PdfFileReader(open(origPDF, "rb"))
    except:
        warnings.warn("could not read " + origPDF)
        return False
    npages = len(input1.pages)
    pdfsize = input1.pages[0].trimbox
    pdfx = int(pdfsize[2])
    pdfy = int(pdfsize[3])
    if verbose:
        print(f"the pdf has size {pdfx}x{pdfy}")

    # rM will not create a file when the page is empty so this is a
    # placeholde empty file to use.
    rm2svg(emptyRm, "tempDir/emptyrm.svg", coloured_annotations=True)

    ratio_rm = 1872 / 1404
    ratio_pdf = pdfy / pdfx
    # rotate landscape pdfs
    landscape = False
    if ratio_pdf < 1:
        if verbose:
            print(f"its landscape format {ratio_pdf}")
        landscape = True

    if ratio_pdf != ratio_rm:
        pdf_obj = resize_pages(origPDF, landscape, verbose=verbose)
        pdf_obj.save("tempdir/resized.pdf") # saves as "resizedPDF"
        resizedPDF = "tempdir/resized.pdf"
        #warnings.warn("The PDF you are annotating has an unexpected size. Annotations may be misaligned.")

    # find what the page hashes are
    content = json.loads(open(refNrPath + ".content").read())
    # convert all pages
    pdflist = []
    for pg, pg_hash in enumerate(content['pages']):
        if verbose:
            print(f"converting page {pg}")
        rmpath = refNrPath + "/" + pg_hash + ".rm"
        if os.path.isfile(rmpath):
            rm2svg(rmpath, "tempDir/temprm" + str(pg) + ".svg", coloured_annotations=False)
            svg_path = "tempDir/temprm" + str(pg) + ".svg"
        else:
            svg_path = "tempDir/emptyrm.svg"
        convertSvg2PdfCmd = "".join(["rsvg-convert -f pdf -a -o ", "tempDir/temppdf" + str(pg), ".pdf ", svg_path])
        os.system(convertSvg2PdfCmd)
        pdflist.append("tempDir/temppdf"+str(pg)+".pdf")
    # merging at high quality gets sooo slow, so we decrease quality for big files
    density_pdf = 200
    quality_pdf = 80
    if pg > 80:
        density_pdf = 100
        quality_pdf = 50

    # merge the annotated pages
    merged_rm = "tempDir/merged_rm.pdf"
    mergeCmd = f"convert -density {density_pdf}x{density_pdf} -quality {quality_pdf} " + (" ").join(pdflist) + " " + merged_rm
    if verbose:
        print(f"Doing Merge: {mergeCmd}")
    #print(mergeCmd)
    os.system(mergeCmd)
    # stamp extracted annotations onto original with pdftk
    stampCmd = "".join(["pdftk ", resizedPDF, " multistamp ", merged_rm, " output ", origPDF[:-4], "_annot.pdf"])
    if verbose:
        print(f"Doing Stamp: {stampCmd}")
    os.system(stampCmd)
    # Remove temporary files
    shutil.rmtree("tempDir", ignore_errors=False, onerror=None)
    return True


def get_target_dimensions(pdfx, pdfy):
    """
    calculates the size to which the base pdf must be scaled to have the same
    page size as the rm. This is necessary to successfully stamp the pages
    together. It also gives a y_offset, because pdf has lower left coordinates
    but the rm displays small pages at the top left.
    """
    ratio_rm = 1872 / 1404
    ratio_pdf = pdfy / pdfx
    if ratio_pdf < ratio_rm:
        keep_side = "x"
        change_side = "y"
    else:
        keep_side = "y"
        change_side = "x"
    size = {"x" : pdfx, "y" : pdfy}

    keep_side_is = size[keep_side]
    change_side_is = size[change_side]

    # <= because on squares, it shouldnt rotate!
    change_side_should = keep_side_is * ratio_rm if keep_side_is <= change_side_is else keep_side_is / ratio_rm

    yoffset = change_side_should - change_side_is if change_side == "y" else 0

    output_size = [keep_side_is, change_side_should] if change_side == "y" else [change_side_should, keep_side_is]
    return output_size, yoffset


def resize_pages(pdfpath, landscape, verbose=False):
    """
    resizes pages using pike pdf to match the remarkable viewport.
    """
    pdf = pikepdf.Pdf.open(pdfpath)
    for i in range(len(pdf.pages)):
        page = pdf.pages[i]
        x = page.trimbox[2]
        y = page.trimbox[3]
        if landscape:
            print("land")
            page.Rotate = 90
            x = page.trimbox[3]
            y = page.trimbox[2]

        if verbose:
            print(f"transforming page {i} to size {x,y}")
        output_size, yoffset = get_target_dimensions(x, y)
        empty_pg = pdf.add_blank_page(page_size=output_size)
        empty_pg.add_overlay(page, pikepdf.Rectangle(0, yoffset, x, y+yoffset))
    del pdf.pages[0:i+1]
    return pdf


if __name__ == "__main__":
    main()
