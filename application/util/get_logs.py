from zipfile import ZipFile
import os 
  
def get_all_file_paths(path_to_logs, archive): 
  paths = os.listdir(path_to_logs)

  for p in paths:
    p = os.path.join(path_to_logs, p)

    if os.path.isdir(p):
      get_all_file_paths(p, archive)

    else:
      archive.write(p)
  return
  
def get_logs(path_to_logs, filename, SAVE_FOLDER): 
  archive = ZipFile(os.path.join(SAVE_FOLDER, filename), "w")

  if os.path.isdir(path_to_logs):
    get_all_file_paths(path_to_logs, archive)

  else:
    archive.write(path_to_logs)

  archive.close()
    
  return True