import pytesseract
from PIL import Image

imagen  = Image.open('ine.jpg')

text = pytesseract.image_to_string(image,lang='spa',config='--psm 6')

print(text)