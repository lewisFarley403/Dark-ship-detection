import os
import json

from pathlib import Path



def create_coco_annotatons(input_json, output_path):
	if os.path.isdir(output_path) is not True:
		print(f'{output_path} Does not exist. Creating directory...')
		Path(output_path).mkdir(parents=True, exist_ok=True)
		print('Directory created successfully!')
	try:
		_ = os.open(input_json,0)
	except FileNotFoundError:
		print(f'{input_json}: File not found')
		return

			
	with open(input_json) as f:
		j = json.load(f)


	id_fn_map = {entry['id']:{'filename':entry['file_name'],'width':entry['width'],'height':entry['height'],'bbox':[]} for entry in j['images']}
	# print(id_fn_map)

	for bbox in j['annotations']:
		#print(bbox)
		width = id_fn_map[bbox['image_id']]['width']
		height = id_fn_map[bbox['image_id']]['height']
		scaled_bbox = bbox['bbox']
		scaled_bbox[0]/=width
		scaled_bbox[1]/=height
		scaled_bbox[2]/=width
		scaled_bbox[3]/=height
		
		id_fn_map[bbox['image_id']]['bbox'].append(scaled_bbox)
	# print(id_fn_map)

	for (key, value) in id_fn_map.items():
		file_name = value['filename']
		file_name=file_name.split('.') [0] + '.txt'
		with open(output_path+file_name,'w') as f:
			# string = '0 '
			string = ''
			for bbox in value['bbox']:
				# print(bbox)
				string +='0 '

				str_bbox = [str(b) for b in bbox]

				string+=' '.join(str_bbox)
				string+='\n'
			# string +='\n'
			f.write(string)
			
if __name__ == '__main__':
	# create the train set
	input_json = 'coco_style/annotations/train.json'
	output_path = 'coco_style/labels/train/'
	create_coco_annotatons(input_json = 'coco_style/annotations/train.json',output_path = 'coco_style/labels/train/')
	# create the test set
	create_coco_annotatons('coco_style/annotations/test_inshore.json','coco_style/labels/test/')
	create_coco_annotatons('coco_style/annotations/test_offshore.json','coco_style/labels/test/')
	create_coco_annotatons('coco_style/annotations/test.json','coco_style/labels/test/')
	n_test = len(os.listdir('coco_style/labels/test/'))
	n_train = len(os.listdir('coco_style/labels/train/'))
	print(f'Successfully created train (n={n_train}) and test (n={n_test}) datasets')