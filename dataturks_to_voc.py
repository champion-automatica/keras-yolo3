import argparse
import sys
import os
import json
import logging
import requests
from collections import OrderedDict

from PIL import Image


#enable info logging.
logging.getLogger().setLevel(logging.INFO)

REPLACE = {
    'Курвуазье VSOP 0.7': 'Курвуазье VSOP',
    'Курвуазье VSOP 0.5': 'Курвуазье VSOP',
    'Джим Бим 0.5': 'Джим Бим',
    'Джим Бим 1': 'Джим Бим',
    'Курвуазье VS 0.7': 'Курвуазье VS',
    'Курвуазье VS 0.5': 'Курвуазье VS',
}

PROCESSED = OrderedDict(files=0)


def maybe_download(image_url, image_dir):
    """Download the image if not already exist, return the location path"""
    fileName = image_url.split("/")[-1]
    filePath = os.path.join(image_dir, fileName)
    if (os.path.exists(filePath)):
        return filePath

    # else download the image
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(filePath, 'wb') as f:
                f.write(response.content)
                return filePath
        else:
            raise ValueError("Not a 200 response")
    except Exception as e:
        logging.exception("Failed to download image at " + image_url + " \n" + str(e) + "\nignoring....")
        raise e


def get_xml_for_bbx(bbx_label, bbx_data, width, height):

    if len(bbx_data['points']) == 4:
        # Regular BBX has 4 points of the rectangle.
        xmin = width * min(bbx_data['points'][0][0], bbx_data['points'][1][0], bbx_data['points'][2][0],
                           bbx_data['points'][3][0])
        ymin = height * min(bbx_data['points'][0][1], bbx_data['points'][1][1], bbx_data['points'][2][1],
                            bbx_data['points'][3][1])

        xmax = width * max(bbx_data['points'][0][0], bbx_data['points'][1][0], bbx_data['points'][2][0],
                           bbx_data['points'][3][0])
        ymax = height * max(bbx_data['points'][0][1], bbx_data['points'][1][1], bbx_data['points'][2][1],
                            bbx_data['points'][3][1])

    else:
        # OCR BBX format has 'x','y' in one point.
        # We store the left top and right bottom as point '0' and point '1'
        xmin = int(bbx_data['points'][0]['x'] * width)
        ymin = int(bbx_data['points'][0]['y'] * height)
        xmax = int(bbx_data['points'][1]['x'] * width)
        ymax = int(bbx_data['points'][1]['y'] * height)

    xml = "<object>\n"
    xml = xml + "\t<name>" + bbx_label + "</name>\n"
    xml = xml + "\t<pose>Unspecified</pose>\n"
    xml = xml + "\t<truncated>Unspecified</truncated>\n"
    xml = xml + "\t<difficult>Unspecified</difficult>\n"
    xml = xml + "\t<occluded>Unspecified</occluded>\n"
    xml = xml + "\t<bndbox>\n"
    xml = xml + "\t\t<xmin>" + str(xmin) + "</xmin>\n"
    xml = xml + "\t\t<xmax>" + str(xmax) + "</xmax>\n"
    xml = xml + "\t\t<ymin>" + str(ymin) + "</ymin>\n"
    xml = xml + "\t\t<ymax>" + str(ymax) + "</ymax>\n"
    xml = xml + "\t</bndbox>\n"
    xml = xml + "</object>\n"
    return xml


def convert_to_PascalVOC(dataturks_labeled_item, image_dir, xml_out_dir):
    """Convert a dataturks labeled item to pascalVOCXML string.
      Args:
        dataturks_labeled_item: JSON of one labeled image from dataturks.
        image_dir: Path to  directory to downloaded images (or a directory already having the images downloaded).
        xml_out_dir: Path to the dir where the xml needs to be written.
      Returns:
        None.
      Raises:
        None.
      """
    try:
        data = json.loads(dataturks_labeled_item)
        if len(data['annotation']) == 0:
            logging.info("Ignoring Skipped Item");
            return False;

        width = data['annotation'][0]['imageWidth']
        height = data['annotation'][0]['imageHeight']
        image_url = data['content']

        filePath = maybe_download(image_url, image_dir)


        with Image.open(filePath) as img:
            width, height = img.size

        fileName = filePath.split("/")[-1]
        image_dir_folder_Name = image_dir.split("/")[-1]

        xml = "<annotation>\n<folder>" + image_dir_folder_Name + "</folder>\n"
        xml = xml + "<filename>" + fileName + "</filename>\n"
        xml = xml + "<path>" + filePath + "</path>\n"
        xml = xml + "<source>\n\t<database>Unknown</database>\n</source>\n"
        xml = xml + "<size>\n"
        xml = xml + "\t<width>" + str(width) + "</width>\n"
        xml = xml + "\t<height>" + str(height) + "</height>\n"
        xml = xml + "\t<depth>Unspecified</depth>\n"
        xml = xml + "</size>\n"
        xml = xml + "<segmented>Unspecified</segmented>\n"

        for bbx in data['annotation']:
            if not bbx:
                continue;
            # Pascal VOC only supports rectangles.
            if "shape" in bbx and bbx["shape"] != "rectangle":
                continue;

            bbx_labels = bbx['label']
            # handle both list of labels or a single label.
            if not isinstance(bbx_labels, list):
                bbx_labels = [bbx_labels]

            for bbx_label in bbx_labels:
                if bbx_label in REPLACE:
                    bbx_label = REPLACE[bbx_label]
                xml = xml + get_xml_for_bbx(bbx_label, bbx, width, height)
                if bbx_label not in PROCESSED:
                    PROCESSED[bbx_label] = 1
                else:
                    PROCESSED[bbx_label] += 1

        xml = xml + "</annotation>"

        # output to a file.
        xmlFilePath = os.path.join(xml_out_dir, fileName + ".xml")
        with open(xmlFilePath, 'w', encoding='utf-8') as f:
            f.write(xml)
        return True
    except Exception as e:
        logging.exception("Unable to process item " + dataturks_labeled_item + "\n" + "error = " + str(e))
        return False


def main():
    # make sure everything is setup.
    if (not os.path.isdir(image_download_dir)):
        logging.exception(
            "Please specify a valid directory path to download images, " + image_download_dir + " doesn't exist")
        return
    if (not os.path.isdir(pascal_voc_xml_dir)):
        logging.exception(
            "Please specify a valid directory path to write Pascal VOC xml files, " + pascal_voc_xml_dir + " doesn't exist")
        return
    if (not os.path.exists(dataturks_JSON_FilePath)):
        logging.exception(
            "Please specify a valid path to dataturks JSON output file, " + dataturks_JSON_FilePath + " doesn't exist")
        return

    lines = []
    with open(dataturks_JSON_FilePath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if (not lines or len(lines) == 0):
        logging.exception(
            "Please specify a valid path to dataturks JSON output file, " + dataturks_JSON_FilePath + " is empty")
        return

    count = 0;
    success = 0
    for line in lines:
        status = convert_to_PascalVOC(line, image_download_dir, pascal_voc_xml_dir)
        if status:
            PROCESSED['files'] += 1

        count += 1
        if count % 10 == 0:
            logging.info(str(count) + " items done ...")

    logging.info('Completed\n{}\nSkipped'.format(PROCESSED, len(lines) - success))


def create_arg_parser():
    """"Creates and returns the ArgumentParser object."""

    parser = argparse.ArgumentParser(
        description='Converts Dataturks output JSON file for Image bounding box to Pascal VOC format.')
    parser.add_argument('dataturks_JSON_FilePath',
                        help='Path to the JSON file downloaded from Dataturks.')
    parser.add_argument('pascal_voc_dir',
                        help='Path to the directory where images and annotations will be stores.')
    parser.add_argument('test_percent', type=float, default=.1,
                        help='Percent that will be taken from whole dataset for test dataset')
    return parser


def process_anotation_dir(image_set_file, image_set):
    with open(image_set_file, 'w') as f:
        for filename in image_set:
            file_annotation = os.path.join(pascal_voc_xml_dir, filename + '.xml')
            new_filename = file_annotation.replace('.jpg', '')
            os.rename(file_annotation, new_filename)
            f.write(filename.replace('.jpg', '') + '\n')


if __name__ == '__main__':
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    global dataturks_JSON_FilePath
    global image_download_dir
    global pascal_voc_xml_dir
    IMAGES_DIR = 'JPEGImages'
    ANNOTATIONS_DIR = 'Annotations'
    IMAGE_SETS_DIR = 'ImageSets/Main'

    pascal_voc_dir = parsed_args.pascal_voc_dir
    create_directories = [IMAGE_SETS_DIR, ANNOTATIONS_DIR, IMAGES_DIR]

    for directory in create_directories:
        path = os.path.join(pascal_voc_dir, directory)
        if not os.path.exists(path):
            os.makedirs(path)

    # setup global paths needed accross the script.
    dataturks_JSON_FilePath = parsed_args.dataturks_JSON_FilePath
    image_download_dir = os.path.join(pascal_voc_dir, IMAGES_DIR)
    pascal_voc_xml_dir = os.path.join(pascal_voc_dir, ANNOTATIONS_DIR)
    image_sets_dir = os.path.join(pascal_voc_dir, IMAGE_SETS_DIR)
    test_percent = parsed_args.test_percent
    print('test percent is {}%'.format(test_percent * 100))
    main()
    create_empty_files = ['train.txt', 'trainval.txt', 'test.txt', 'val.txt']
    for filename in create_empty_files:
        filepath = os.path.join(image_sets_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        with open(filepath, 'w') as f:
            f.write('')

    images = os.listdir(image_download_dir)
    test_count = int(len(images) * test_percent)
    test_set = images[:test_count]
    trainval_set = images[test_count:]

    process_anotation_dir(os.path.join(image_sets_dir, 'trainval.txt'), trainval_set)
    process_anotation_dir(os.path.join(image_sets_dir, 'test.txt'), test_set)
