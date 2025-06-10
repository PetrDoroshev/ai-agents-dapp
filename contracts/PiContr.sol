// SPDX-License-Identifier: MIT
// pragma solidity >=0.8.0 <0.9.0;
pragma solidity 0.8.17;

import "./IERC20.sol";

contract PiContr {
    struct AIRun {
        address requester;
        string inputDataLink;
        bytes32 inputDataHash;
        string outputDataLink;
        bytes32 outputDataHash;
        string randomState;
    }

    address public owner;
    uint public price;
    uint public runCounter;
    uint public runPriceTokens;

    IERC20 public token;

    mapping(uint => AIRun) public runs;

    event RunRequested(uint256 indexed runId, address indexed requester, string inputDataLink, bytes32 inputDataHash, string randomState);
    event RunCompleted(uint256 indexed runId, string outputDataLink, bytes32 outputDataHash);

    constructor(address tokenAddress, uint runPrice) {
        owner = msg.sender;
        token = IERC20(tokenAddress);
        runPriceTokens = runPrice;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    function requestRun(string memory _inputDataLink, bytes32 _inputDataHash, string memory _randomState) external payable {
        require(msg.value >= runPriceTokens, "Insufficient payment");

        runCounter += 1;
        runs[runCounter] = AIRun({
            requester: msg.sender,
            inputDataLink: _inputDataLink,
            inputDataHash: _inputDataHash,
            outputDataLink: "",
            outputDataHash: 0,
            randomState: _randomState
        });

        emit RunRequested(runCounter, msg.sender, _inputDataLink, _inputDataHash, _randomState);
    }

    function submitRunResult(uint256 _runId, string memory _outputDataLink, bytes32 _outputDataHash) external onlyOwner {
        AIRun storage run = runs[_runId];
        require(run.requester != address(0), "Run does not exist");

        run.outputDataLink = _outputDataLink;
        run.outputDataHash = _outputDataHash;

        emit RunCompleted(_runId, _outputDataLink, _outputDataHash);
    }

    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    function updateRunPrice(uint256 _newPrice) external onlyOwner {
        runPriceTokens = _newPrice;
    }
}
