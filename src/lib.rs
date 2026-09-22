#![forbid(unsafe_code)]

mod lexer;
mod parser;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// Repair malformed JSON and return a valid JSON string.
///
/// Raises ValueError when the input exceeds 128 nested containers.
#[pyfunction(name = "repair")]
fn py_repair(py: Python<'_>, input: &str) -> PyResult<String> {
    py.detach(|| parser::repair(input))
        .map_err(|error| PyValueError::new_err(error.to_string()))
}

/// Compatibility alias for `repair`.
#[pyfunction]
fn repair_to_string(py: Python<'_>, input: &str) -> PyResult<String> {
    py_repair(py, input)
}

/// Compatibility alias for `repair`.
#[pyfunction]
fn repair_json(py: Python<'_>, input: &str) -> PyResult<String> {
    py_repair(py, input)
}

/// Repair malformed JSON and deserialize it with Python's standard `json` module.
#[pyfunction]
fn loads(py: Python<'_>, input: &str) -> PyResult<Py<PyAny>> {
    let repaired = py_repair(py, input)?;
    let json = PyModule::import(py, "json")?;
    let value = json.call_method1("loads", (repaired,))?;
    Ok(value.unbind())
}

#[pymodule]
fn repairjson(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("MAX_DEPTH", parser::MAX_DEPTH)?;
    m.add_function(wrap_pyfunction!(py_repair, m)?)?;
    m.add_function(wrap_pyfunction!(repair_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(repair_json, m)?)?;
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    Ok(())
}
