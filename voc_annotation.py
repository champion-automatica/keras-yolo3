import xml.etree.ElementTree as ET
from os import getcwd

sets = [('2007', 'trainval'), ('2007', 'test')]

classes = ['Джим Бим', 'Джим Бим Apple', 'Джим Бим Черри', 'Курвуазье VS', 'Курвуазье VSOP', 'Сауза Голд', 'Сауза Сильвер']


def convert_annotation(year, image_id, list_file):
    in_file = open('VOCdevkit/VOC%s/Annotations/%s.xml' % (year, image_id))
    tree = ET.parse(in_file)
    root = tree.getroot()

    for obj in root.iter('object'):
        difficult = obj.find('difficult').text
        cls = obj.find('name').text
        if cls not in classes:
            continue
        cls_id = classes.index(cls)
        xmlbox = obj.find('bndbox')
        b = int(float(xmlbox.find('xmin').text)), int(float((xmlbox.find('ymin').text))), int(
            float(xmlbox.find('xmax').text)), int(float(xmlbox.find('ymax').text))
        list_file.write(" " + ",".join([str(a) for a in b]) + ',' + str(cls_id))


wd = getcwd()

for year, image_set in sets:
    image_ids = open('VOCdevkit/VOC%s/ImageSets/Main/%s.txt' % (year, image_set)).read().strip().split()
    list_file = open('%s_%s.txt' % (year, image_set), 'w')
    for image_id in image_ids:
        list_file.write('%s/VOCdevkit/VOC%s/JPEGImages/%s.jpg' % (wd, year, image_id))
        convert_annotation(year, image_id, list_file)
        list_file.write('\n')
    list_file.close()
