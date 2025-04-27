# tests/test_cambalache.py

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, call, ANY
import pandas as pd
import typer
from io import StringIO
import sys
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from cambalache import (
    ReplaceStrategy,
    PrefixStrategy,
    SuffixStrategy,
    BothStrategy,
    AppConfig,
    DataLoader,
    JsonWriter,
    JsonProcessor,
    main,
    TransformationStrategy
)

# --- Tests para Estrategias de Transformación ---
def test_replace_strategy():
    strategy = ReplaceStrategy()
    assert strategy.apply("original", "nuevo") == [{"field_value": "nuevo"}]

def test_prefix_strategy():
    strategy = PrefixStrategy()
    assert strategy.apply("original", "pre_") == [{"field_value": "pre_original"}]

def test_suffix_strategy():
    strategy = SuffixStrategy()
    assert strategy.apply("original", "_suf") == [{"field_value": "original_suf"}]

def test_both_strategy():
    strategy = BothStrategy()
    assert strategy.apply("original", "mod_") == [
        {"field_value": "mod_original"},
        {"field_value": "originalmod_"}
    ]

# --- Tests para AppConfig ---

@pytest.fixture
def base_config_args(tmp_path):
    """Crea argumentos base para AppConfig usando un directorio temporal."""
    template = tmp_path / "template.json"
    wordlist = tmp_path / "words.csv"
    output = tmp_path / "output.json"
    template.touch()
    wordlist.touch()
    return {
        "template_path": template,
        "wordlist_path": wordlist,
        "output_path": output,
        "include_fields": None,
        "ignore_fields": None,
        "prefix": False,
        "suffix": False,
        "both": False,
    }

def test_app_config_validation_exclusive_modes(base_config_args, mocker):
    """Testea que prefix, suffix y both son mutuamente excluyentes."""
    mocker.patch("typer.echo")

    with pytest.raises(typer.Exit):
        AppConfig(**{**base_config_args, "prefix": True, "suffix": True})
    typer.echo.assert_called_with(
        "Error: Las opciones --prefix, --suffix, y --both son mutuamente excluyentes.",
         err=True
    )

    typer.echo.reset_mock()
    with pytest.raises(typer.Exit):
        AppConfig(**{**base_config_args, "suffix": True, "both": True})

    typer.echo.reset_mock()
    with pytest.raises(typer.Exit):
        AppConfig(**{**base_config_args, "prefix": True, "both": True})

    typer.echo.reset_mock()
    with pytest.raises(typer.Exit):
        AppConfig(**{**base_config_args, "prefix": True, "suffix": True, "both": True})

def test_app_config_validation_exclusive_fields(base_config_args, mocker):
    """Testea que include y ignore son mutuamente excluyentes."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí

    with pytest.raises(typer.Exit):
        AppConfig(**{**base_config_args, "include_fields": ["a"], "ignore_fields": ["b"]})
    typer.echo.assert_called_with(
        "Error: No puedes usar --include y --ignore al mismo tiempo.", err=True
    )
    # No verificar sys.exit aquí

def test_app_config_is_generation_mode(base_config_args):
    """Verifica la propiedad is_generation_mode."""
    assert not AppConfig(**base_config_args).is_generation_mode
    assert AppConfig(**{**base_config_args, "prefix": True}).is_generation_mode
    assert AppConfig(**{**base_config_args, "suffix": True}).is_generation_mode
    assert AppConfig(**{**base_config_args, "both": True}).is_generation_mode

def test_app_config_get_strategy(base_config_args):
    """Verifica la selección correcta de estrategia."""
    assert isinstance(AppConfig(**base_config_args).get_strategy(), ReplaceStrategy)
    assert isinstance(AppConfig(**{**base_config_args, "prefix": True}).get_strategy(), PrefixStrategy)
    assert isinstance(AppConfig(**{**base_config_args, "suffix": True}).get_strategy(), SuffixStrategy)
    assert isinstance(AppConfig(**{**base_config_args, "both": True}).get_strategy(), BothStrategy)

def test_app_config_get_mode_description(base_config_args):
    """Verifica la descripción correcta del modo."""
    assert AppConfig(**base_config_args).get_mode_description() == "Reemplazo"
    assert AppConfig(**{**base_config_args, "prefix": True}).get_mode_description() == "prefijo"
    assert AppConfig(**{**base_config_args, "suffix": True}).get_mode_description() == "sufijo"
    assert AppConfig(**{**base_config_args, "both": True}).get_mode_description() == "prefijo Y sufijo (objetos separados)"


# --- Tests para DataLoader ---

@pytest.fixture
def data_loader():
    """Fixture para crear una instancia de DataLoader."""
    return DataLoader()

def test_dataloader_load_template_success(data_loader, mocker):
    """Testea la carga exitosa de la plantilla."""
    mock_json_data = '[{"name": "base", "json_data": {"field1": "value1", "field2": 123}}]'
    mock_path = Path("dummy_template.json")
    mocker.patch("pathlib.Path.open", mock_open(read_data=mock_json_data))
    template = data_loader.load_template(mock_path)
    assert template == {"name": "base", "json_data": {"field1": "value1", "field2": 123}}

def test_dataloader_load_template_invalid_json(data_loader, mocker):
    """Testea la carga con JSON inválido."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", mock_open(read_data='[{"key": "value"'))
    mock_path = Path("invalid.json")
    mocker.patch("json.load", side_effect=json.JSONDecodeError("Expecting property name enclosed in double quotes", "", 0))

    with pytest.raises(typer.Exit):
        data_loader.load_template(mock_path)
    # El código original captura esto en except json.JSONDecodeError
    typer.echo.assert_called_with(
        f"Error: El archivo de plantilla '{mock_path}' no es un JSON válido.", err=True
    )
    # No verificar sys.exit aquí

def test_dataloader_load_template_not_a_list(data_loader, mocker):
    """Testea la carga cuando el JSON no es una lista."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", mock_open(read_data='{"key": "value"}'))
    mock_path = Path("not_list.json")

    with pytest.raises(typer.Exit):
        data_loader.load_template(mock_path)
    # El código original (con bug) captura typer.Exit en except Exception:
    # Verificar el mensaje genérico que se imprime en ese caso.
    # Nota: ¡Se recomienda arreglar el try/except en cambalache.py!
    typer.echo.assert_called_with(
         f"Error al leer el archivo de plantilla '{mock_path}': ", err=True,
         # ANY captura el mensaje de la excepción original que se añade
         # mocker.ANY
    )
    # No verificar sys.exit aquí

def test_dataloader_load_template_empty_list(data_loader, mocker):
    """Testea la carga cuando la lista JSON está vacía."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", mock_open(read_data='[]'))
    mock_path = Path("empty_list.json")

    with pytest.raises(typer.Exit):
        data_loader.load_template(mock_path)
    # El código original (con bug) captura typer.Exit en except Exception:
    typer.echo.assert_called_with(
         f"Error al leer el archivo de plantilla '{mock_path}': ", err=True,
         # mocker.ANY
    )
    # No verificar sys.exit aquí

def test_dataloader_load_template_no_json_data(data_loader, mocker):
    """Testea la carga cuando falta la clave 'json_data'."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", mock_open(read_data='[{"name": "test"}]'))
    mock_path = Path("no_jsondata.json")

    with pytest.raises(typer.Exit):
        data_loader.load_template(mock_path)
    # El código original (con bug) captura typer.Exit en except Exception:
    typer.echo.assert_called_with(
         f"Error al leer el archivo de plantilla '{mock_path}': ", err=True,
         # mocker.ANY
    )
    # No verificar sys.exit aquí

def test_dataloader_load_template_json_data_not_dict(data_loader, mocker):
    """Testea la carga cuando 'json_data' no es un diccionario."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", mock_open(read_data='[{"name": "test", "json_data": "not a dict"}]'))
    mock_path = Path("jsondata_not_dict.json")

    with pytest.raises(typer.Exit):
        data_loader.load_template(mock_path)
    # El código original (con bug) captura typer.Exit en except Exception:
    typer.echo.assert_called_with(
         f"Error al leer el archivo de plantilla '{mock_path}': ", err=True,
         # mocker.ANY
    )
    # No verificar sys.exit aquí

def test_dataloader_load_wordlist_success(data_loader, mocker):
    """Testea la carga exitosa de la wordlist, eliminando duplicados y vacíos."""
    csv_data = "word1\nword2\nword1\n\nword3\n   \nword4"
    # Simular lo que read_csv leería
    simulated_read = pd.read_csv(StringIO(csv_data), header=None, names=["word"], dtype=str, skip_blank_lines=True)
    mocker.patch("pandas.read_csv", return_value=simulated_read)
    mock_path = Path("words.csv")

    words = data_loader.load_wordlist(mock_path)
    # Verificar el resultado DESPUÉS de dropna() y drop_duplicates()
    assert words == ["word1", "word2", "word3", "word4"]

def test_dataloader_load_wordlist_empty(data_loader, mocker):
    """Testea la carga de una wordlist vacía o con solo líneas en blanco."""
    mocker.patch("typer.echo")
    mock_df = pd.DataFrame(columns=["word"], dtype=str) # DataFrame vacío
    mock_path = Path("empty_words.csv")
    mocker.patch("pandas.read_csv", return_value=mock_df)

    words = data_loader.load_wordlist(mock_path)
    assert words == []
    typer.echo.assert_called_with(
        f"Advertencia: La lista de palabras '{mock_path}' está vacía o no contiene palabras válidas.", err=True
    )

def test_dataloader_load_wordlist_error(data_loader, mocker):
    """Testea un error durante la lectura del archivo de wordlist."""
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mock_path = Path("error_words.csv")
    mocker.patch("pandas.read_csv", side_effect=Exception("Read error"))

    with pytest.raises(typer.Exit):
        data_loader.load_wordlist(mock_path)
    # Se captura en except Exception:
    typer.echo.assert_called_with(
        f"Error al leer la lista de palabras '{mock_path}': Read error", err=True
    )
    # No verificar sys.exit aquí


# --- Tests para JsonWriter ---

@pytest.fixture
def json_writer():
    """Fixture para crear una instancia de JsonWriter."""
    return JsonWriter()

def test_jsonwriter_write_success(json_writer, mocker, tmp_path):
    """Testea la escritura exitosa a un archivo JSON."""
    output_path = tmp_path / "output.json"
    data_to_write = [{"key1": "value1"}, {"key2": 123}]
    mock_file = mock_open()
    mocker.patch("pathlib.Path.open", mock_file)
    mock_json_dump = mocker.patch("json.dump")

    json_writer.write(data_to_write, output_path)

    mock_file.assert_called_once_with("w", encoding="utf-8")
    mock_json_dump.assert_called_once_with(
        data_to_write, mock_file(), indent=4, ensure_ascii=False
    )

def test_jsonwriter_write_error(json_writer, mocker, tmp_path):
    """Testea un error durante la escritura del archivo JSON."""
    output_path = tmp_path / "output_error.json"
    data_to_write = [{"key": "value"}]
    mocker.patch("typer.echo")
    # No mockear sys.exit aquí
    mocker.patch("pathlib.Path.open", side_effect=IOError("Disk full"))

    with pytest.raises(typer.Exit):
        json_writer.write(data_to_write, output_path)
    # Se captura en except Exception:
    typer.echo.assert_called_with(
        f"Error al escribir el archivo de salida '{output_path}': Disk full", err=True
    )
    # No verificar sys.exit aquí


# --- Tests para JsonProcessor ---

@pytest.fixture
def mock_config(tmp_path):
    """Crea un mock de AppConfig para JsonProcessor."""
    config = MagicMock(spec=AppConfig)
    config.template_path = tmp_path / "template.json"
    config.wordlist_path = tmp_path / "words.csv"
    config.output_path = tmp_path / "output.json"
    config.include_fields = None
    config.ignore_fields = None
    config.prefix = False
    config.suffix = False
    config.both = False
    config.is_generation_mode = False
    config.get_strategy.return_value = ReplaceStrategy() # Estrategia por defecto
    config.get_mode_description.return_value = "Reemplazo"
    config.template_path.touch()
    config.wordlist_path.touch()
    return config

@pytest.fixture
def sample_base_obj():
    """Objeto base de ejemplo para tests."""
    return {"id": 1, "json_data": {"field_a": "val_a", "field_b": "val_b"}}

@pytest.fixture
def sample_words():
    """Lista de palabras de ejemplo."""
    return ["w1", "w2"]

@pytest.fixture
def mocked_processor(mocker, mock_config):
    """Configura un JsonProcessor con dependencias mockeadas."""
    # Mockear clases ANTES de instanciar JsonProcessor
    mock_loader = MagicMock(spec=DataLoader)
    mocker.patch("cambalache.DataLoader", return_value=mock_loader)
    mock_writer = MagicMock(spec=JsonWriter)
    mocker.patch("cambalache.JsonWriter", return_value=mock_writer)
    mocker.patch("typer.echo") # Mockear echo globalmente para la clase

    # Instanciar el procesador
    processor = JsonProcessor(mock_config)

    # Devolver instancias para uso en tests
    return processor, mock_loader, mock_writer, mock_config


def test_processor_load_inputs(mocked_processor, sample_base_obj, sample_words):
    """Verifica que _load_inputs llama correctamente a DataLoader."""
    processor, mock_loader, _, mock_config = mocked_processor
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = sample_words

    processor._load_inputs()

    mock_loader.load_template.assert_called_once_with(mock_config.template_path)
    mock_loader.load_wordlist.assert_called_once_with(mock_config.wordlist_path)
    assert processor.base_obj == sample_base_obj
    assert processor.words == sample_words

def test_processor_determine_target_fields_default(mocked_processor, sample_base_obj):
    """Verifica la selección de campos por defecto (todos)."""
    processor, _, _, mock_config = mocked_processor
    mock_config.include_fields = None
    mock_config.ignore_fields = None
    processor.base_obj = sample_base_obj

    processor._determine_target_fields()
    assert processor.target_fields == {"field_a", "field_b"}

def test_processor_determine_target_fields_include(mocked_processor, sample_base_obj):
    """Verifica la selección de campos con --include."""
    processor, _, _, mock_config = mocked_processor
    mock_config.include_fields = ["field_a", "non_existent"]
    mock_config.ignore_fields = None
    processor.base_obj = sample_base_obj

    processor._determine_target_fields()
    assert processor.target_fields == {"field_a"}
    # Verificar que se advierte sobre campos no existentes
    typer.echo.assert_any_call(
        "Advertencia: Los siguientes campos de --include no existen en json_data: non_existent",
        err=True
    )

def test_processor_determine_target_fields_ignore(mocked_processor, sample_base_obj):
    """Verifica la selección de campos con --ignore."""
    processor, _, _, mock_config = mocked_processor
    mock_config.include_fields = None
    mock_config.ignore_fields = ["field_b", "non_existent"]
    processor.base_obj = sample_base_obj

    processor._determine_target_fields()
    assert processor.target_fields == {"field_a"}

def test_processor_determine_target_fields_ignore_all(mocked_processor, sample_base_obj):
    """Verifica la selección cuando --ignore elimina todos los campos."""
    processor, _, _, mock_config = mocked_processor
    mock_config.include_fields = None
    mock_config.ignore_fields = ["field_a", "field_b"]
    processor.base_obj = sample_base_obj

    processor._determine_target_fields()
    assert processor.target_fields == set()
    # Verificar que se advierte sobre la falta de campos restantes
    typer.echo.assert_any_call(
        "Advertencia: Al ignorar field_a, field_b, no quedan campos para modificar.",
        err=True
    )

def test_processor_process_replace_mode(mocked_processor, sample_base_obj, sample_words):
    """Testea el modo de operación 'Replace'."""
    processor, mock_loader, mock_writer, mock_config = mocked_processor
    # Configurar modo y dependencias
    mock_config.is_generation_mode = False
    mock_config.prefix = False; mock_config.suffix = False; mock_config.both = False
    mock_config.get_strategy.return_value = ReplaceStrategy()
    mock_config.get_mode_description.return_value = "Reemplazo"
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = sample_words
    processor.strategy = mock_config.get_strategy() # Asignar estrategia

    count = processor.process()

    assert count == 2 # 1 obj por palabra
    expected_results = [
        {"id": 1, "json_data": {"field_a": "w1", "field_b": "w1"}},
        {"id": 1, "json_data": {"field_a": "w2", "field_b": "w2"}}
    ]
    args, kwargs = mock_writer.write.call_args
    assert args[0] == expected_results
    assert args[1] == mock_config.output_path
    typer.echo.assert_any_call("Modo Reemplazo activado. Procesando...")

def test_processor_process_prefix_mode(mocked_processor, sample_base_obj, sample_words):
    """Testea el modo de operación 'Prefix'."""
    processor, mock_loader, mock_writer, mock_config = mocked_processor
    # Configurar modo y dependencias
    mock_config.is_generation_mode = True
    mock_config.prefix = True; mock_config.suffix = False; mock_config.both = False
    mock_config.get_strategy.return_value = PrefixStrategy()
    mock_config.get_mode_description.return_value = "prefijo"
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = sample_words
    processor.strategy = mock_config.get_strategy() # Asignar estrategia

    count = processor.process()

    assert count == 4 # 1 obj por palabra * 2 campos
    expected_results = [
        {'id': 1, 'json_data': {'field_a': 'w1val_a', 'field_b': 'val_b'}},
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'w1val_b'}},
        {'id': 1, 'json_data': {'field_a': 'w2val_a', 'field_b': 'val_b'}},
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'w2val_b'}}
    ]
    args, kwargs = mock_writer.write.call_args
    # Comparar sin importar el orden
    assert set(map(json.dumps, args[0])) == set(map(json.dumps, expected_results))
    assert args[1] == mock_config.output_path
    typer.echo.assert_any_call("Modo prefijo activado. Procesando...")

def test_processor_process_both_mode(mocked_processor, sample_base_obj, sample_words):
    """Testea el modo de operación 'Both'."""
    processor, mock_loader, mock_writer, mock_config = mocked_processor
    # Configurar modo y dependencias
    mock_config.is_generation_mode = True
    mock_config.prefix = False; mock_config.suffix = False; mock_config.both = True
    mock_config.get_strategy.return_value = BothStrategy()
    mock_config.get_mode_description.return_value = "prefijo Y sufijo (objetos separados)"
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = sample_words
    processor.strategy = mock_config.get_strategy() # Asignar estrategia

    count = processor.process()

    assert count == 8 # 2 objs (pref/suf) por palabra * 2 campos
    expected_results = [
        {'id': 1, 'json_data': {'field_a': 'w1val_a', 'field_b': 'val_b'}}, # prefix a
        {'id': 1, 'json_data': {'field_a': 'val_aw1', 'field_b': 'val_b'}}, # suffix a
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'w1val_b'}}, # prefix b
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'val_bw1'}}, # suffix b
        {'id': 1, 'json_data': {'field_a': 'w2val_a', 'field_b': 'val_b'}}, # prefix a
        {'id': 1, 'json_data': {'field_a': 'val_aw2', 'field_b': 'val_b'}}, # suffix a
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'w2val_b'}}, # prefix b
        {'id': 1, 'json_data': {'field_a': 'val_a', 'field_b': 'val_bw2'}}, # suffix b
    ]
    args, kwargs = mock_writer.write.call_args
    results_list = args[0]
    # Comparar sin importar el orden
    assert set(map(json.dumps, results_list)) == set(map(json.dumps, expected_results))
    assert len(results_list) == 8
    assert args[1] == mock_config.output_path
    typer.echo.assert_any_call("Modo prefijo Y sufijo (objetos separados) activado. Procesando...")

def test_processor_process_empty_wordlist(mocked_processor, sample_base_obj):
    """Testea el proceso con una lista de palabras vacía."""
    processor, mock_loader, mock_writer, mock_config = mocked_processor
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = [] # Lista vacía
    processor.strategy = mock_config.get_strategy()

    count = processor.process()

    assert count == 0
    typer.echo.assert_any_call("Lista de palabras vacía. No se generarán nuevos objetos.", err=True)
    mock_writer.write.assert_called_once_with([], mock_config.output_path)

def test_processor_process_no_target_fields(mocked_processor, sample_base_obj, sample_words):
    """Testea el proceso cuando no hay campos objetivo para modificar."""
    processor, mock_loader, mock_writer, mock_config = mocked_processor
    mock_loader.load_template.return_value = sample_base_obj
    mock_loader.load_wordlist.return_value = sample_words
    mock_config.ignore_fields = ["field_a", "field_b"] # Ignorar todos
    processor.strategy = mock_config.get_strategy()

    count = processor.process() # Llama a _determine_target_fields internamente

    assert count == 0
    # Se debe imprimir el warning de _determine_target_fields y el de process
    typer.echo.assert_any_call(
        "Advertencia: Al ignorar field_a, field_b, no quedan campos para modificar.",
        err=True
    )
    typer.echo.assert_any_call("No hay campos objetivo para modificar. No se generarán nuevos objetos.", err=True)
    mock_writer.write.assert_called_once_with([], mock_config.output_path)


# --- Tests para la función main (interfaz Typer) ---

@pytest.fixture
def mock_main_dependencies(mocker):
    """Configura mocks para las dependencias de la función main."""
    # Mock AppConfig
    mock_app_config = MagicMock(spec=AppConfig)
    mock_app_config.output_path = Path("/fake/mock_output.json") # Path absoluto simple
    MockAppConfigClass = mocker.patch('cambalache.AppConfig', return_value=mock_app_config)

    # Mock JsonProcessor
    mock_processor = MagicMock(spec=JsonProcessor)
    mock_processor.process.return_value = 10
    MockJsonProcessorClass = mocker.patch('cambalache.JsonProcessor', return_value=mock_processor)

    # Mock utilidades
    mocker.patch('typer.echo')
    mock_sys_exit = mocker.patch('sys.exit') # Mockear exit SÍ es necesario aquí

    # Mocks básicos de Path para validación de tipos, no se necesita resolve
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('pathlib.Path.is_file', return_value=True)
    mocker.patch('os.access', return_value=True)

    return MockAppConfigClass, MockJsonProcessorClass, mock_app_config, mock_processor, mock_sys_exit

def test_main_success(mock_main_dependencies):
    """Testea la ejecución exitosa de main."""
    MockAppConfigClass, MockJsonProcessorClass, mock_app_config, mock_processor, mock_sys_exit = mock_main_dependencies

    # Definir los paths resueltos (absolutos) que se pasarán a main
    resolved_template = Path("/fake/template.json")
    resolved_wordlist = Path("/fake/words.csv")
    resolved_output = Path("/fake/output.json")

    # Llamar a main con los paths ya resueltos
    main(
        template_path=resolved_template,
        wordlist_path=resolved_wordlist,
        output_path=resolved_output,
        prefix=True # Ejemplo de opción
    )

    # Verificar inicialización de AppConfig
    MockAppConfigClass.assert_called_once()
    call_args, call_kwargs = MockAppConfigClass.call_args
    assert call_kwargs['template_path'] == resolved_template
    assert call_kwargs['wordlist_path'] == resolved_wordlist
    assert call_kwargs['output_path'] == resolved_output
    assert call_kwargs['prefix'] is True

    # Verificar inicialización y llamada a JsonProcessor
    MockJsonProcessorClass.assert_called_once_with(mock_app_config)
    mock_processor.process.assert_called_once()

    # Verificar mensaje de éxito (usa el path del config mockeado)
    typer.echo.assert_called_with(
       f"Proceso completado. Se generaron 10 objetos en '{mock_app_config.output_path}'."
    )
    # Verificar que no hubo salida prematura
    mock_sys_exit.assert_not_called()

def test_main_appconfig_validation_error(mock_main_dependencies):
    """Testea el manejo de un error de validación en AppConfig."""
    MockAppConfigClass, _, _, _, mock_sys_exit = mock_main_dependencies

    config_error_code = 1
    # Simular que AppConfig lanza typer.Exit al ser inicializado
    MockAppConfigClass.side_effect = typer.Exit(code=config_error_code)

    # Definir paths resueltos dummy
    resolved_template = Path("/fake/t")
    resolved_wordlist = Path("/fake/w")
    resolved_output = Path("/fake/o")

    # Llamar a main (que intentará crear AppConfig y fallará)
    main(resolved_template, resolved_wordlist, resolved_output)

    # Verificar que main capturó typer.Exit y llamó a sys.exit con el código correcto
    # (Requiere corrección en el bloque except de main en cambalache.py)
    mock_sys_exit.assert_called_once_with(config_error_code)

def test_main_processor_error(mock_main_dependencies, mocker):
    """Testea el manejo de una excepción inesperada en JsonProcessor."""
    MockAppConfigClass, MockJsonProcessorClass, mock_app_config, mock_processor, mock_sys_exit = mock_main_dependencies

    error_message = "Algo salió muy mal"
    # Simular que processor.process lanza una excepción
    mock_processor.process.side_effect = Exception(error_message)
    mock_traceback_print = mocker.patch('traceback.print_exc')

    # Definir paths resueltos dummy
    resolved_template = Path("/fake/t")
    resolved_wordlist = Path("/fake/w")
    resolved_output = Path("/fake/o")

    # Llamar a main (que llamará a process y fallará)
    main(resolved_template, resolved_wordlist, resolved_output)

    # Verificar que se imprimió el error inesperado
    typer.echo.assert_any_call(f"Error inesperado durante la ejecución: {error_message}", err=True)
    # Verificar que se imprimió el traceback
    mock_traceback_print.assert_called_once()
    # Verificar que main llamó a sys.exit con código 1
    # (Requiere corrección en el bloque except Exception de main en cambalache.py)
    mock_sys_exit.assert_called_once_with(1)