# =============================================================================
# TEST 3: EVENT-DRIVEN PIPELINE SISTEMI
# Zorluk: ZOR | Callback, closure, decorator, dinamik dispatch
# =============================================================================
# Beklenen: LLM muhtemelen hata yapacak
# Potansiyel Halusinasyonlar:
#   - Decorator'lari fonksiyon cagrisi sanma
#   - Callback'leri yanlis yorumlama
#   - Closure'daki dolayli cagrilari kacirma
#   - Lambda icindeki cagrilari atlama

from functools import wraps

# ==================== DECORATORS ====================
def log_execution(func):
    """Fonksiyon calismasini loglar - BU BIR CAGRI DEGIL!"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        _write_log(f"Executing: {func.__name__}")
        result = func(*args, **kwargs)
        _write_log(f"Completed: {func.__name__}")
        return result
    return wrapper

def validate_input(func):
    """Girdiyi dogrular - BU BIR CAGRI DEGIL!"""
    @wraps(func)
    def wrapper(data, *args, **kwargs):
        if not _is_valid(data):
            _handle_validation_error(data)
            return None
        return func(data, *args, **kwargs)
    return wrapper

def _write_log(message):
    pass

def _is_valid(data):
    return data is not None

def _handle_validation_error(data):
    _write_log("Validation failed")


# ==================== EVENT SYSTEM ====================
class EventBus:
    _handlers = {}

    @classmethod
    def subscribe(cls, event_name, handler):
        """Handler'i kaydeder - handler BURADA CAGRILMAZ!"""
        if event_name not in cls._handlers:
            cls._handlers[event_name] = []
        cls._handlers[event_name].append(handler)

    @classmethod
    def publish(cls, event_name, data):
        """Event yayinlar - handler'lar BURADA cagrilir."""
        if event_name in cls._handlers:
            for handler in cls._handlers[event_name]:
                handler(data)  # Dinamik cagri!

    @classmethod
    def clear(cls):
        cls._handlers = {}


# ==================== PIPELINE ====================
class DataPipeline:
    def __init__(self):
        self.stages = []
        self._setup_error_handling()

    def _setup_error_handling(self):
        """Error handler'i KAYDEDER, cagirmaz!"""
        EventBus.subscribe("error", self._on_error)

    def _on_error(self, error_data):
        """Error oldugunda cagrilir."""
        _write_log(f"Error: {error_data}")
        self._rollback()

    def _rollback(self):
        _write_log("Rolling back...")

    def add_stage(self, stage_func):
        """Stage ekler - stage_func BURADA CAGRILMAZ!"""
        self.stages.append(stage_func)
        return self  # Method chaining icin

    @log_execution  # Decorator - cagri DEGIL!
    def execute(self, initial_data):
        """Pipeline'i calistirir."""
        data = initial_data
        for stage in self.stages:
            data = stage(data)  # Dinamik cagri!
            if data is None:
                EventBus.publish("error", "Stage failed")
                return None
        self._on_complete(data)
        return data

    def _on_complete(self, result):
        EventBus.publish("complete", result)


# ==================== STAGE FONKSIYONLARI ====================
@validate_input  # Decorator - cagri DEGIL!
def stage_parse(data):
    """Veriyi parse eder."""
    return _parse_json(data)

def _parse_json(data):
    return {"parsed": data}

@validate_input
def stage_transform(data):
    """Veriyi donusturur."""
    return _apply_transformation(data)

def _apply_transformation(data):
    result = _normalize(data)
    result = _enrich(result)
    return result

def _normalize(data):
    return data

def _enrich(data):
    data["enriched"] = True
    return data

@validate_input
def stage_validate(data):
    """Veriyi dogrular."""
    if _check_schema(data):
        return data
    return None

def _check_schema(data):
    return "parsed" in data

@log_execution
def stage_save(data):
    """Veriyi kaydeder."""
    _write_to_storage(data)
    return data

def _write_to_storage(data):
    pass


# ==================== CALLBACK FACTORY ====================
def create_completion_handler(callback_name):
    """Closure icinde callback olusturur."""
    def handler(result):
        _write_log(f"Handler {callback_name} called")
        _process_result(result)  # Bu cagri closure icinde!
    return handler

def _process_result(result):
    _write_log("Processing result")


# ==================== ANA FONKSIYON ====================
def run_pipeline(input_data):
    """
    Ana fonksiyon - DIKKAT:
    - Decorator'lar CAGRI DEGIL, fonksiyon sarmalayici
    - subscribe() handler'i KAYIT EDER, cagirmaz
    - add_stage() fonksiyonu KAYIT EDER, cagirmaz
    - execute() icinde stage'ler DINAMIK cagrilir
    """
    # Completion handler'i KAYDET (cagirma!)
    completion_handler = create_completion_handler("main")
    EventBus.subscribe("complete", completion_handler)

    # Pipeline olustur ve stage'leri KAYDET (cagirma!)
    pipeline = DataPipeline()
    pipeline.add_stage(stage_parse)      # Kayit, cagri degil!
    pipeline.add_stage(stage_transform)  # Kayit, cagri degil!
    pipeline.add_stage(stage_validate)   # Kayit, cagri degil!
    pipeline.add_stage(stage_save)       # Kayit, cagri degil!

    # SIMDI calistir - stage'ler BURADA cagrilir
    result = pipeline.execute(input_data)

    return result


# =============================================================================
# GERCEK CALL GRAPH (LLM bunlari bulmali):
# =============================================================================
# run_pipeline
#   --> create_completion_handler (closure olusturur)
#   --> EventBus.subscribe (handler'i KAYDEDER)
#   --> DataPipeline.__init__
#       --> _setup_error_handling --> EventBus.subscribe
#   --> pipeline.add_stage (4 kez, kayit)
#   --> pipeline.execute (@log_execution decorator wrapper calisir)
#       --> _write_log (decorator icinden)
#       --> stage_parse (@validate_input wrapper)
#           --> _is_valid
#           --> _parse_json
#       --> stage_transform
#           --> _is_valid
#           --> _apply_transformation --> _normalize, _enrich
#       --> stage_validate
#           --> _is_valid
#           --> _check_schema
#       --> stage_save (@log_execution wrapper)
#           --> _write_log
#           --> _write_to_storage
#       --> _on_complete --> EventBus.publish
#           --> completion_handler (dinamik!) --> _write_log, _process_result
#
# =============================================================================
# LLM'IN YAPACAGI MUHTEMEL HATALAR:
# =============================================================================
# 1. @log_execution'i "run_pipeline --> log_execution" cagrisi sanmak
# 2. subscribe(handler)'i "hemen cagriliyor" sanmak
# 3. add_stage(func)'i "hemen cagriliyor" sanmak
# 4. Closure icindeki _process_result cagrisini kacirmak
# 5. Decorator wrapper icindeki _write_log cagrisini kacirmak
# =============================================================================
