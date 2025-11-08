import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class MockMongoCollection:
    def __init__(self, name: str, db_file: str = "data.json"):
        self.name = name
        self.db_file = db_file
        self._ensure_db()
    
    def _ensure_db(self):
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({}, f)
    
    def _read_db(self) -> Dict:
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _write_db(self, data: Dict):
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def find_one(self, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        db = self._read_db()
        collection_data = db.get(self.name, [])
        
        for doc in collection_data:
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                if projection:
                    result = {}
                    for k, v in projection.items():
                        if v == 0 and k != "_id":
                            continue
                        elif k in doc:
                            result[k] = doc[k]
                    return result if result else doc
                return doc
        return None
    
    def insert_one(self, document: Dict) -> Any:
        db = self._read_db()
        if self.name not in db:
            db[self.name] = []
        
        doc_with_id = document.copy()
        if "_id" not in doc_with_id:
            doc_with_id["_id"] = str(len(db[self.name]) + 1)
        
        db[self.name].append(doc_with_id)
        self._write_db(db)
        
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        
        return InsertResult(doc_with_id["_id"])
    
    def update_one(self, query: Dict, update: Dict, upsert: bool = False) -> Any:
        db = self._read_db()
        collection_data = db.get(self.name, [])
        
        for i, doc in enumerate(collection_data):
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            
            if match:
                if "$push" in update:
                    for key, value in update["$push"].items():
                        if key not in doc:
                            doc[key] = []
                        doc[key].append(value)
                
                if "$set" in update:
                    for key, value in update["$set"].items():
                        doc[key] = value
                
                collection_data[i] = doc
                db[self.name] = collection_data
                self._write_db(db)
                
                class UpdateResult:
                    def __init__(self):
                        self.modified_count = 1
                
                return UpdateResult()
        
        if upsert:
            new_doc = query.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            self.insert_one(new_doc)
        
        class UpdateResult:
            def __init__(self):
                self.modified_count = 0
        
        return UpdateResult()


class MockMongoClient:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.databases = {}
    
    def __getitem__(self, db_name: str):
        if db_name not in self.databases:
            self.databases[db_name] = MockMongoDatabase(db_name)
        return self.databases[db_name]


class MockMongoDatabase:
    def __init__(self, name: str):
        self.name = name
        self.collections = {}
    
    def __getitem__(self, collection_name: str):
        if collection_name not in self.collections:
            self.collections[collection_name] = MockMongoCollection(
                f"{self.name}_{collection_name}"
            )
        return self.collections[collection_name]
