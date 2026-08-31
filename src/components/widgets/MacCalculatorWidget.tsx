import { useState } from "react";

interface MacCalculatorWidgetProps {
  onClose?: () => void;
}

export function MacCalculatorWidget({ onClose }: MacCalculatorWidgetProps) {
  const [display, setDisplay] = useState("0");
  const [equation, setEquation] = useState("");
  const [prevValue, setPrevValue] = useState<number | null>(null);
  const [operation, setOperation] = useState<string | null>(null);
  const [waitingForOperand, setWaitingForOperand] = useState(false);

  function inputDigit(digit: string) {
    if (waitingForOperand) {
      setDisplay(digit);
      setWaitingForOperand(false);
    } else {
      setDisplay(display === "0" ? digit : display + digit);
    }
  }

  function inputDot() {
    if (waitingForOperand) {
      setDisplay("0.");
      setWaitingForOperand(false);
    } else if (!display.includes(".")) {
      setDisplay(display + ".");
    }
  }

  function clearAll() {
    setDisplay("0");
    setEquation("");
    setPrevValue(null);
    setOperation(null);
    setWaitingForOperand(false);
  }

  function toggleSign() {
    const val = parseFloat(display);
    if (!isNaN(val)) {
      setDisplay(String(-val));
    }
  }

  function inputPercent() {
    const val = parseFloat(display);
    if (!isNaN(val)) {
      setDisplay(String(val / 100));
    }
  }

  function performOperation(nextOp: string) {
    const inputValue = parseFloat(display);

    if (prevValue === null) {
      setPrevValue(inputValue);
      setEquation(`${inputValue} ${nextOp}`);
    } else if (operation) {
      const current = prevValue;
      let newValue = current;

      if (operation === "+") newValue = current + inputValue;
      else if (operation === "−") newValue = current - inputValue;
      else if (operation === "×") newValue = current * inputValue;
      else if (operation === "÷") newValue = inputValue === 0 ? 0 : current / inputValue;

      setPrevValue(newValue);
      setDisplay(String(newValue));
      setEquation(`${current} ${operation} ${inputValue}`);
    }

    setWaitingForOperand(true);
    setOperation(nextOp);
  }

  function calculateEquals() {
    if (operation === null || prevValue === null) return;
    const inputValue = parseFloat(display);
    let result = prevValue;

    if (operation === "+") result = prevValue + inputValue;
    else if (operation === "−") result = prevValue - inputValue;
    else if (operation === "×") result = prevValue * inputValue;
    else if (operation === "÷") result = inputValue === 0 ? 0 : prevValue / inputValue;

    setEquation(`${prevValue} ${operation} ${inputValue} =`);
    setDisplay(String(result));
    setPrevValue(null);
    setOperation(null);
    setWaitingForOperand(true);
  }

  return (
    <div className="mac-calculator-card" aria-label="macOS Floating Calculator">
      {/* Calculator Header with Traffic Lights */}
      <div className="mac-calc-header">
        <div className="mac-traffic-lights">
          <button type="button" className="traffic-light traffic-light--red" onClick={onClose} title="Close Calculator" />
          <button type="button" className="traffic-light traffic-light--yellow" onClick={clearAll} title="Clear (AC)" />
          <button type="button" className="traffic-light traffic-light--green" title="Maximize" />
        </div>
      </div>

      {/* Screen Display */}
      <div className="mac-calc-display-area">
        <div className="mac-calc-equation">{equation}</div>
        <div className="mac-calc-number">{display}</div>
      </div>

      {/* Calculator Keypad Grid */}
      <div className="mac-calc-keypad">
        <button type="button" className="calc-key calc-key--top" onClick={clearAll}>
          {display === "0" ? "AC" : "C"}
        </button>
        <button type="button" className="calc-key calc-key--top" onClick={toggleSign}>
          ±
        </button>
        <button type="button" className="calc-key calc-key--top" onClick={inputPercent}>
          %
        </button>
        <button type="button" className="calc-key calc-key--op" onClick={() => performOperation("÷")}>
          ÷
        </button>

        <button type="button" className="calc-key" onClick={() => inputDigit("7")}>
          7
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("8")}>
          8
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("9")}>
          9
        </button>
        <button type="button" className="calc-key calc-key--op" onClick={() => performOperation("×")}>
          ×
        </button>

        <button type="button" className="calc-key" onClick={() => inputDigit("4")}>
          4
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("5")}>
          5
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("6")}>
          6
        </button>
        <button type="button" className="calc-key calc-key--op" onClick={() => performOperation("−")}>
          −
        </button>

        <button type="button" className="calc-key" onClick={() => inputDigit("1")}>
          1
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("2")}>
          2
        </button>
        <button type="button" className="calc-key" onClick={() => inputDigit("3")}>
          3
        </button>
        <button type="button" className="calc-key calc-key--op" onClick={() => performOperation("+")}>
          +
        </button>

        <button type="button" className="calc-key calc-key--zero" onClick={() => inputDigit("0")}>
          0
        </button>
        <button type="button" className="calc-key" onClick={inputDot}>
          .
        </button>
        <button type="button" className="calc-key calc-key--op" onClick={calculateEquals}>
          =
        </button>
      </div>
    </div>
  );
}

