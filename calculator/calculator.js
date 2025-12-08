const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function calculate(num1, operator, num2) {
  switch (operator) {
    case '+':
      return num1 + num2;
    case '-':
      return num1 - num2;
    case '*':
      return num1 * num2;
    case '/':
      if (num2 === 0) {
        throw new Error('Division by zero is not allowed');
      }
      return num1 / num2;
    default:
      throw new Error('Invalid operator. Use +, -, *, or /');
  }
}

function isValidNumber(str) {
  return !isNaN(str) && !isNaN(parseFloat(str));
}

function askForCalculation() {
  rl.question('Enter first number: ', (num1Str) => {
    if (!isValidNumber(num1Str)) {
      console.log('Invalid number. Please try again.');
      return askForCalculation();
    }

    const num1 = parseFloat(num1Str);

    rl.question('Enter operator (+, -, *, /): ', (operator) => {
      if (!['+', '-', '*', '/'].includes(operator)) {
        console.log('Invalid operator. Please use +, -, *, or /');
        return askForCalculation();
      }

      rl.question('Enter second number: ', (num2Str) => {
        if (!isValidNumber(num2Str)) {
          console.log('Invalid number. Please try again.');
          return askForCalculation();
        }

        const num2 = parseFloat(num2Str);

        try {
          const result = calculate(num1, operator, num2);
          console.log(`Result: ${num1} ${operator} ${num2} = ${result}`);
        } catch (error) {
          console.log(`Error: ${error.message}`);
        }

        rl.question('Do you want to perform another calculation? (y/n): ', (answer) => {
          if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
            askForCalculation();
          } else {
            console.log('Goodbye!');
            rl.close();
          }
        });
      });
    });
  });
}

console.log('Welcome to the CLI Calculator!');
console.log('Supported operations: +, -, *, /');
askForCalculation();