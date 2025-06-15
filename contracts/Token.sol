// SPDX-License-Identifier: MIT

//pragma solidity >=0.8.0 <0.9.0;
pragma solidity 0.8.17;

import "./IERC20.sol";

contract MyToken is IERC20 {
    uint256 private constant MAX_UINT256 = 2 ** 256 - 1;
    uint256 public rate = 1000;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowed;

 	string public _name;
    string public _symbol;
    uint8 public _decimals;
    uint256 private _totalSupply;

    address public acc_owner;

    constructor(string memory name_, string memory symbol_, uint8 decimals_) {
        _name = name_;
        _symbol = symbol_;
        _decimals = decimals_;
        acc_owner = msg.sender;
    }

    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address owner) public view returns (uint256) {
        return _balances[owner];
    }

    function allowance(
        address owner,
        address spender
    ) public view returns (uint256) {
        return _allowed[owner][spender];
    }

    function transfer(address to, uint256 value) public returns (bool) {
        require(value <= _balances[msg.sender]);

        _balances[msg.sender] -= value;
        _balances[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) public returns (bool) {
        _allowed[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) public returns (bool) {
        require(value <= _balances[from]);
        require(value <= _allowed[from][msg.sender]);

        _balances[from] -= value;
        _balances[to] += value;
        if (_allowed[from][msg.sender] < MAX_UINT256) {
            _allowed[from][msg.sender] -= value;
        }
        emit Transfer(from, to, value);
        return true;
    }

    modifier onlyOwner() {
        require(msg.sender == acc_owner, "Not the owner");
        _;
    }

    function mint(address to, uint256 amount) public onlyOwner returns (bool) {
        require(to != address(0), "Mint to zero address");

        _totalSupply += amount;
        _balances[to] += amount;

        emit Transfer(address(0), to, amount);
        return true;
    }

    receive() external payable {
        exchangeEthToTokens();
    }

    function exchangeEthToTokens() public payable {
        require(msg.value > 0, "Send ETH to buy tokens");
        uint256 tokenAmount = (msg.value * rate) / 1 ether;

        require(_balances[acc_owner] >= tokenAmount, "Not enough tokens in reserve");
        
        _balances[acc_owner] -= tokenAmount;
        _balances[msg.sender] += tokenAmount;

        emit Transfer(acc_owner, msg.sender, tokenAmount);
    }
}
