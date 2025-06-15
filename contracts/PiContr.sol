// SPDX-License-Identifier: MIT
// pragma solidity >=0.8.0 <0.9.0;
pragma solidity 0.8.17;

import "./IERC20.sol";

contract PiContr {
    enum Status { Requested, Completed, Cancelled, Refunded }

    struct AIRun {
        address requester;
        string inputDataLink;
        bytes32 inputDataHash;
        string outputDataLink;
        bytes32 outputDataHash;
        string randomState;
        Status status;
    }

    address public owner;
    uint public price;
    uint public runCounter;
    uint public runPriceTokens;

    IERC20 public token;

    mapping(uint => AIRun) public runs;
    mapping(address => uint[]) public userRuns;

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

    function requestRun(address requester, string memory _inputDataLink, bytes32 _inputDataHash, string memory _randomState, uint256 thisRunPrice) external onlyOwner {
        require(token.balanceOf(requester) >= thisRunPrice, "Insufficient Tokens");
        token.transferFrom(requester, address(this), thisRunPrice);

        runCounter += 1;

        userRuns[requester].push(runCounter);
        runs[runCounter] = AIRun({
            requester: requester,
            inputDataLink: _inputDataLink,
            inputDataHash: _inputDataHash,
            outputDataLink: "",
            outputDataHash: 0,
            randomState: _randomState,
            status: Status.Requested
        });

        emit RunRequested(runCounter, msg.sender, _inputDataLink, _inputDataHash, _randomState);
    }

    function submitRunResult(uint256 _runId, string memory _outputDataLink, bytes32 _outputDataHash, Status _newStatus) external onlyOwner {
        AIRun storage run = runs[_runId];
        require(run.requester != address(0), "Run does not exist");

        run.outputDataLink = _outputDataLink;
        run.outputDataHash = _outputDataHash;
        run.status = _newStatus;

        emit RunCompleted(_runId, _outputDataLink, _outputDataHash);
    }

    function runsOf(address user) external view returns (AIRun[] memory) {
        uint[] storage ids = userRuns[user];
        AIRun[] memory out = new AIRun[](ids.length);
        for (uint i = 0; i < ids.length; i++) {
            out[i] = runs[ids[i]];
        }
        return out;
    }


    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    function updateRunPrice(uint256 _newPrice) external onlyOwner {
        runPriceTokens = _newPrice;
    }

    function withdrawTo(address payable recipient, uint256 amount) public onlyOwner {
        require(recipient != address(0), "Invalid recipient");
        require(address(this).balance >= amount, "Not enough ETH in contract");
        recipient.transfer(amount);
    }
}
