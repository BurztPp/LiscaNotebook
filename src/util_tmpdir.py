from tempfile import TemporaryFile

def mktmpf(tmpdir=".", prefix="_tmp_pyama_"):
    return TemporaryFile(dir=tmpdir, prefix=prefix)
    
