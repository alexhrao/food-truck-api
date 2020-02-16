from flask import Flask, Response, request
from google.cloud import storage, firestore
from flask_cors import CORS
import base64
import json

db = firestore.Client()

app = Flask(__name__)
CORS(app)

@app.route('/api/views/<string:view>')
def get_live_view(view):
    doc = db.collection('images').document(view).get()
    filename = doc.get('lastSnapshot.filename')
    time_updated = doc.get('lastSnapshot.updateTime')
    if filename is None or filename == '':
        return ({
            'data': '',
            'time': '',
        })
    file_data = str(base64.b64encode(storage.Client().bucket(view).blob(filename).download_as_string()), encoding='utf-8')
    return ({
        'data': file_data,
        'time': time_updated.isoformat()
    })
@app.route('/api/views')
def get_views():
    docs = [{ 'id': d.id, 'display': d.get().to_dict()['display_name'] } for d in db.collection('last-view').list_documents()]
    return json.dumps(docs)

# Image Document output looks like this:
"""
{
    'key': 'filename',
    'bucket': 'bucket-name',
    'filename': 'filename.png',
    'valid': bool,
    'labels': [
        {
            'groupName': 'group-name',
            'groupType': 'single'|'multiple'|'numeric'
            'labels': 'label-name'|['label-names']|number
        },
        {
            'groupName': 'group-name',
            'groupType': 'single'|'multiple'|'numeric'
            'labels': 'label-name'|['label-names']|number
        },...
    ]
}
"""
@app.route('/api/images/<string:bucket_name>/<string:image_name>', methods=['GET'])
def get_image_metadata(bucket_name='', image_name=''):
    if bucket_name == '':
        # No bucket - just get the first one that hasn't been seen!
        docs = list(db.collection_group('labels').where('seen', '==', False).limit(1).stream())
        if len(docs) == 0:
            return {}
        doc = docs[0]
        return get_image_metadata(doc.get('bucket'), doc.id)
    doc_ref = db.collection('images').document(bucket_name).collection('labels').document(image_name)
    doc = doc_ref.get()
    if not doc.exists:
        return {}
    out = {
        'key': image_name,
        'bucket': bucket_name,
        'filename': '{0}.png'.format(image_name),
        'valid': doc.get('valid'),
        'seen': doc.get('seen'),
        'labels': list()
    }
    for labelGroup in doc.get('labels'):
        label = labelGroup.get('group').get()
        out['labels'].append({
            'groupName': label.id,
            'groupType': label.get('groupType'),
            'labels': labelGroup.get('values')
        })
    return out

@app.route('/api/images/', methods=['GET'])
def get_next_image():
    return get_image_metadata()

@app.route('/api/images/<string:bucket_name>/<string:image_name>', methods=['PUT'])
def update_image_metadata(bucket_name, image_name):
    labels = request.get_json(force=True)
    doc_ref = db.collection('images').document(bucket_name).collection('labels').document(image_name)
    doc = doc_ref.get()
    curr_label_groups = list(doc.get('labels'))
    curr_labels = [ lab.get('group').id for lab in doc.get('labels')]
    if len(labels) == 0:
        doc_ref.update({ 'valid': False })
    else:
        doc_ref.update({ 'valid': True })
    for label in labels:
        # each label looks like { labelGroup: 'group-name', value: val }
        group_ref = db.collection('label-groups').document(label['labelGroup'])
        if label['labelGroup'] in curr_labels:
            ind = curr_labels.index(label['labelGroup'])
            tmp = curr_label_groups.pop(ind)
            doc_ref.update({
                'labels': firestore.ArrayRemove([tmp])
            })
        doc_ref.update({
            'labels': firestore.ArrayUnion([{
                'group': group_ref,
                'values': label['value']
            }])
        })
    doc_ref.update({ 'seen': True })

    return {}
    # TODO: Post request with label data

@app.route('/api/snapshots/<string:bucket_name>/<string:image_name>')
def snapshot(bucket_name, image_name):
    file_ref = storage.Client().bucket(bucket_name).blob('{0}.png'.format(image_name))
    file_data = file_ref.download_as_string()
    resp = Response(file_data)
    resp.headers['Content-Type'] = file_ref.content_type
    return resp

@app.route('/api/labels')
def get_labels():
    out = list()
    for label in db.collection('label-groups').stream():
        tmp = label.to_dict()
        tmp['groupName'] = label.id
        out.append(tmp)
    return json.dumps(out)
if __name__=='__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)