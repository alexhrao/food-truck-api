from flask import Flask, Response, request
from google.cloud import storage, firestore
from flask_cors import CORS
import base64
import json
from datetime import datetime, timedelta

if __name__ == '__main__':
    db = firestore.Client()
    store = storage.Client()
    docs = db.collection_group('labels').where('valid', '==', False).where('seen', '==', True).limit(1).stream()
    for doc in docs:
        print(doc.id)
        blob = store.bucket(doc.get('bucket')).blob(doc.get('filename'))
        blob.delete()
        doc.reference.delete()
